#!/bin/bash
# AWS 인프라 프로비저닝 스크립트
# 사용법: ./provision_aws.sh

set -e

# 설정
PROJECT_NAME="drama-shorts"
REGION="ap-northeast-2"  # 서울
INSTANCE_TYPE="t3.micro"
ENVIRONMENT="production"

# 로그 파일 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/provision_$(date '+%Y%m%d_%H%M%S').log"

# 모든 출력을 터미널과 로그 파일에 동시 기록
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== $PROJECT_NAME AWS 인프라 프로비저닝 ==="
echo "로그 파일: $LOG_FILE"
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 0. 사전 검증
echo "[0/8] 사전 검증..."
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "❌ 오류: 기본 VPC가 존재하지 않습니다."
    echo "   AWS 콘솔에서 기본 VPC를 생성하거나 VPC ID를 직접 지정하세요."
    exit 1
fi
echo "✓ 기본 VPC 확인: $VPC_ID"

# 최신 Ubuntu 24.04 LTS AMI 조회
echo "  최신 Ubuntu AMI 조회 중..."
AMI_ID=$(aws ssm get-parameters \
    --names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
    --region $REGION \
    --query 'Parameters[0].Value' \
    --output text 2>/dev/null)

if [ "$AMI_ID" = "None" ] || [ -z "$AMI_ID" ]; then
    echo "⚠ SSM에서 AMI를 찾을 수 없어 EC2 API로 조회합니다..."
    AMI_ID=$(aws ec2 describe-images \
        --region $REGION \
        --owners 099720109477 \
        --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
        --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
        --output text)
fi

if [ "$AMI_ID" = "None" ] || [ -z "$AMI_ID" ]; then
    echo "❌ 오류: Ubuntu 24.04 AMI를 찾을 수 없습니다."
    exit 1
fi
echo "✓ Ubuntu 24.04 AMI: $AMI_ID"

# 1. 키 페어 생성
echo "[1/8] 키 페어 생성..."
if ! aws ec2 describe-key-pairs --key-names ${PROJECT_NAME}-key --region $REGION &>/dev/null; then
    aws ec2 create-key-pair \
        --key-name ${PROJECT_NAME}-key \
        --region $REGION \
        --query 'KeyMaterial' \
        --output text > ${PROJECT_NAME}-key.pem
    chmod 400 ${PROJECT_NAME}-key.pem
    echo "✓ 키 페어 생성: ${PROJECT_NAME}-key.pem"
else
    echo "✓ 키 페어 이미 존재"
fi

# 2. 보안 그룹 생성
echo "[2/8] 보안 그룹 생성..."
if ! aws ec2 describe-security-groups --group-names ${PROJECT_NAME}-sg --region $REGION &>/dev/null; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-sg \
        --description "Security group for ${PROJECT_NAME}" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${PROJECT_NAME}-sg},{Key=Project,Value=${PROJECT_NAME}},{Key=Environment,Value=${ENVIRONMENT}}]" \
        --query 'GroupId' \
        --output text)

    # SSH (22)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    # HTTP (80)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    # HTTPS (443)
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION

    echo "✓ 보안 그룹 생성: $SG_ID"
else
    SG_ID=$(aws ec2 describe-security-groups --group-names ${PROJECT_NAME}-sg --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
    echo "✓ 보안 그룹 이미 존재: $SG_ID"
fi

# 3. S3 버킷 생성 (IAM Role 정책에 필요하므로 먼저 생성)
echo "[3/8] S3 버킷 생성..."
BUCKET_NAME="${PROJECT_NAME}-media-$(aws sts get-caller-identity --query 'Account' --output text)"

if ! aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $REGION \
        --create-bucket-configuration LocationConstraint=$REGION

    # 퍼블릭 액세스 차단 (보안)
    aws s3api put-public-access-block \
        --bucket $BUCKET_NAME \
        --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

    # 버킷 태깅
    aws s3api put-bucket-tagging \
        --bucket $BUCKET_NAME \
        --tagging "TagSet=[{Key=Name,Value=${BUCKET_NAME}},{Key=Project,Value=${PROJECT_NAME}},{Key=Environment,Value=${ENVIRONMENT}}]"

    echo "✓ S3 버킷 생성: $BUCKET_NAME"
else
    echo "✓ S3 버킷 이미 존재: $BUCKET_NAME"
fi

# 4. IAM Role 생성 (EC2용 - Access Key 대신 사용)
echo "[4/8] IAM Role 생성..."
IAM_ROLE="${PROJECT_NAME}-ec2-role"
INSTANCE_PROFILE="${PROJECT_NAME}-ec2-profile"

if ! aws iam get-role --role-name $IAM_ROLE &>/dev/null; then
    # Trust Policy (EC2가 이 역할을 맡을 수 있도록)
    TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
)

    aws iam create-role \
        --role-name $IAM_ROLE \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "EC2 role for ${PROJECT_NAME}" \
        --tags Key=Project,Value=${PROJECT_NAME} Key=Environment,Value=${ENVIRONMENT}

    # S3 접근 정책
    S3_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF
)

    aws iam put-role-policy \
        --role-name $IAM_ROLE \
        --policy-name ${PROJECT_NAME}-s3-policy \
        --policy-document "$S3_POLICY"

    # Instance Profile 생성 및 역할 연결
    aws iam create-instance-profile --instance-profile-name $INSTANCE_PROFILE
    aws iam add-role-to-instance-profile \
        --instance-profile-name $INSTANCE_PROFILE \
        --role-name $IAM_ROLE

    # Instance Profile이 사용 가능해질 때까지 대기
    echo "  Instance Profile 준비 대기 중..."
    sleep 10

    echo "✓ IAM Role 생성: $IAM_ROLE"
else
    echo "✓ IAM Role 이미 존재: $IAM_ROLE"
fi

# 5. EC2 인스턴스 생성
echo "[5/8] EC2 인스턴스 생성..."
EXISTING_INSTANCE=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=${PROJECT_NAME}" "Name=instance-state-name,Values=running,pending,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null)

if [ "$EXISTING_INSTANCE" = "None" ] || [ -z "$EXISTING_INSTANCE" ]; then
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --key-name ${PROJECT_NAME}-key \
        --security-group-ids $SG_ID \
        --iam-instance-profile Name=$INSTANCE_PROFILE \
        --region $REGION \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT_NAME}},{Key=Project,Value=${PROJECT_NAME}},{Key=Environment,Value=${ENVIRONMENT}}]" \
        --query 'Instances[0].InstanceId' \
        --output text)

    echo "✓ 인스턴스 생성 중: $INSTANCE_ID"
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    echo "✓ 인스턴스 실행 완료"
else
    INSTANCE_ID=$EXISTING_INSTANCE
    echo "✓ 인스턴스 이미 존재: $INSTANCE_ID"

    # 기존 인스턴스에 IAM Role 연결 (없는 경우)
    ATTACHED_PROFILE=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --region $REGION \
        --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' \
        --output text 2>/dev/null)

    if [ "$ATTACHED_PROFILE" = "None" ] || [ -z "$ATTACHED_PROFILE" ]; then
        echo "  기존 인스턴스에 IAM Role 연결 중..."
        aws ec2 associate-iam-instance-profile \
            --instance-id $INSTANCE_ID \
            --iam-instance-profile Name=$INSTANCE_PROFILE \
            --region $REGION 2>/dev/null || echo "  ⚠ IAM Role 연결 실패 (이미 연결되어 있을 수 있음)"
    fi
fi

# 6. Elastic IP 할당
echo "[6/8] Elastic IP 할당..."
EXISTING_EIP=$(aws ec2 describe-addresses \
    --region $REGION \
    --filters "Name=tag:Name,Values=${PROJECT_NAME}" \
    --query 'Addresses[0].PublicIp' \
    --output text 2>/dev/null)

if [ "$EXISTING_EIP" = "None" ] || [ -z "$EXISTING_EIP" ]; then
    ALLOCATION_ID=$(aws ec2 allocate-address \
        --domain vpc \
        --region $REGION \
        --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${PROJECT_NAME}},{Key=Project,Value=${PROJECT_NAME}},{Key=Environment,Value=${ENVIRONMENT}}]" \
        --query 'AllocationId' \
        --output text)

    aws ec2 associate-address \
        --instance-id $INSTANCE_ID \
        --allocation-id $ALLOCATION_ID \
        --region $REGION

    ELASTIC_IP=$(aws ec2 describe-addresses --allocation-ids $ALLOCATION_ID --region $REGION --query 'Addresses[0].PublicIp' --output text)
    echo "✓ Elastic IP 할당: $ELASTIC_IP"
else
    ELASTIC_IP=$EXISTING_EIP
    echo "✓ Elastic IP 이미 존재: $ELASTIC_IP"
fi

# 7. 크레덴셜 파일 생성
echo "[7/8] 크레덴셜 파일 생성..."
CREDENTIALS_FILE="${PROJECT_NAME}-credentials.txt"

cat > "$CREDENTIALS_FILE" <<EOF
# ${PROJECT_NAME} AWS 크레덴셜
# 생성일: $(date '+%Y-%m-%d %H:%M:%S')
# ⚠️ 이 파일을 안전하게 보관하고 Git에 커밋하지 마세요!

EC2_INSTANCE_ID=$INSTANCE_ID
ELASTIC_IP=$ELASTIC_IP
S3_BUCKET=$BUCKET_NAME
IAM_ROLE=$IAM_ROLE
REGION=$REGION

# .env에 추가할 내용:
DJANGO_ALLOWED_HOSTS=$ELASTIC_IP,drama.buuup.kr
DJANGO_CSRF_TRUSTED_ORIGINS=http://$ELASTIC_IP,https://drama.buuup.kr
AWS_STORAGE_BUCKET_NAME=$BUCKET_NAME
AWS_S3_REGION_NAME=$REGION

# EC2는 IAM Role을 사용하므로 Access Key가 필요 없습니다.
# AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY는 비워두세요.
EOF

chmod 600 "$CREDENTIALS_FILE"
echo "✓ 크레덴셜 파일 생성: $CREDENTIALS_FILE"

# 8. 결과 출력
echo ""
echo "[8/8] 완료!"
echo "========================================"
echo "EC2 Instance ID: $INSTANCE_ID"
echo "Elastic IP: $ELASTIC_IP"
echo "S3 Bucket: $BUCKET_NAME"
echo "IAM Role: $IAM_ROLE"
echo "AMI: $AMI_ID"
echo "========================================"
echo ""
echo ".env에 추가할 내용:"
echo "----------------------------------------"
echo "DJANGO_ALLOWED_HOSTS=$ELASTIC_IP,drama.buuup.kr"
echo "DJANGO_CSRF_TRUSTED_ORIGINS=http://$ELASTIC_IP,https://drama.buuup.kr"
echo "AWS_STORAGE_BUCKET_NAME=$BUCKET_NAME"
echo "AWS_S3_REGION_NAME=$REGION"
echo ""
echo "# EC2는 IAM Role을 사용하므로 Access Key 불필요"
echo "# AWS_ACCESS_KEY_ID="
echo "# AWS_SECRET_ACCESS_KEY="
echo "----------------------------------------"
echo ""
echo "크레덴셜 상세 정보: cat $CREDENTIALS_FILE"
echo ""
echo "EC2 접속:"
echo "ssh -i ${PROJECT_NAME}-key.pem ubuntu@$ELASTIC_IP"
echo ""
echo "========================================"
echo "Cloudflare SSL 설정 (Full Strict 모드)"
echo "========================================"
echo "1. Cloudflare 대시보드 → SSL/TLS → Origin Server"
echo "2. 'Create Certificate' 클릭"
echo "3. 생성된 인증서를 EC2에 저장:"
echo "   - /etc/ssl/cloudflare/origin.pem (Certificate)"
echo "   - /etc/ssl/cloudflare/origin-key.pem (Private Key)"
echo "4. Nginx/Caddy에서 해당 인증서 사용 설정"
echo "5. Cloudflare SSL/TLS 모드를 'Full (strict)'로 설정"
echo ""
echo "DNS 설정:"
echo "- A 레코드: drama.buuup.kr → $ELASTIC_IP (Proxied)"
echo "========================================"
echo ""
echo "완료 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo "로그 파일: $LOG_FILE"
