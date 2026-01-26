#!/bin/bash
# AWS 인프라 프로비저닝 스크립트
# 사용법: ./provision_aws.sh

set -e

# 설정
PROJECT_NAME="drama-shorts"
REGION="ap-northeast-2"  # 서울
INSTANCE_TYPE="t3.micro"
AMI_ID="ami-0c2acfcb2ac4d02a0"  # Ubuntu 24.04 LTS (ap-northeast-2)

echo "=== $PROJECT_NAME AWS 인프라 프로비저닝 ==="

# 1. 키 페어 생성
echo "[1/7] 키 페어 생성..."
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
echo "[2/7] 보안 그룹 생성..."
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

if ! aws ec2 describe-security-groups --group-names ${PROJECT_NAME}-sg --region $REGION &>/dev/null; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-sg \
        --description "Security group for ${PROJECT_NAME}" \
        --vpc-id $VPC_ID \
        --region $REGION \
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

    echo "✓ 보안 그룹 생성: $SG_ID"
else
    SG_ID=$(aws ec2 describe-security-groups --group-names ${PROJECT_NAME}-sg --region $REGION --query 'SecurityGroups[0].GroupId' --output text)
    echo "✓ 보안 그룹 이미 존재: $SG_ID"
fi

# 3. EC2 인스턴스 생성
echo "[3/7] EC2 인스턴스 생성..."
EXISTING_INSTANCE=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=${PROJECT_NAME}" "Name=instance-state-name,Values=running,pending,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null)

if [ "$EXISTING_INSTANCE" == "None" ] || [ -z "$EXISTING_INSTANCE" ]; then
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --instance-type $INSTANCE_TYPE \
        --key-name ${PROJECT_NAME}-key \
        --security-group-ids $SG_ID \
        --region $REGION \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT_NAME}}]" \
        --query 'Instances[0].InstanceId' \
        --output text)

    echo "✓ 인스턴스 생성 중: $INSTANCE_ID"
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    echo "✓ 인스턴스 실행 완료"
else
    INSTANCE_ID=$EXISTING_INSTANCE
    echo "✓ 인스턴스 이미 존재: $INSTANCE_ID"
fi

# 4. Elastic IP 할당
echo "[4/7] Elastic IP 할당..."
EXISTING_EIP=$(aws ec2 describe-addresses \
    --region $REGION \
    --filters "Name=tag:Name,Values=${PROJECT_NAME}" \
    --query 'Addresses[0].PublicIp' \
    --output text 2>/dev/null)

if [ "$EXISTING_EIP" == "None" ] || [ -z "$EXISTING_EIP" ]; then
    ALLOCATION_ID=$(aws ec2 allocate-address \
        --domain vpc \
        --region $REGION \
        --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${PROJECT_NAME}}]" \
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

# 5. S3 버킷 생성
echo "[5/7] S3 버킷 생성..."
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

    echo "✓ S3 버킷 생성: $BUCKET_NAME"
else
    echo "✓ S3 버킷 이미 존재: $BUCKET_NAME"
fi

# 6. IAM 사용자 생성 (S3 접근용)
echo "[6/7] IAM 사용자 생성..."
IAM_USER="${PROJECT_NAME}-s3-user"

if ! aws iam get-user --user-name $IAM_USER &>/dev/null; then
    aws iam create-user --user-name $IAM_USER

    # S3 정책 생성 및 연결
    POLICY_DOC=$(cat <<EOF
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

    aws iam put-user-policy \
        --user-name $IAM_USER \
        --policy-name ${PROJECT_NAME}-s3-policy \
        --policy-document "$POLICY_DOC"

    # 액세스 키 생성
    ACCESS_KEY=$(aws iam create-access-key --user-name $IAM_USER --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
    AWS_ACCESS_KEY_ID=$(echo $ACCESS_KEY | awk '{print $1}')
    AWS_SECRET_ACCESS_KEY=$(echo $ACCESS_KEY | awk '{print $2}')

    echo "✓ IAM 사용자 생성: $IAM_USER"
else
    echo "✓ IAM 사용자 이미 존재: $IAM_USER"
    echo "⚠ 기존 액세스 키를 사용하거나 새로 생성하세요"
    AWS_ACCESS_KEY_ID="<existing-key>"
    AWS_SECRET_ACCESS_KEY="<existing-secret>"
fi

# 7. 결과 출력
echo ""
echo "[7/7] 완료!"
echo "========================================"
echo "EC2 Instance ID: $INSTANCE_ID"
echo "Elastic IP: $ELASTIC_IP"
echo "S3 Bucket: $BUCKET_NAME"
echo "========================================"
echo ""
echo ".env에 추가할 내용:"
echo "----------------------------------------"
echo "DJANGO_ALLOWED_HOSTS=$ELASTIC_IP,your-domain.com"
echo "DJANGO_CSRF_TRUSTED_ORIGINS=http://$ELASTIC_IP,https://your-domain.com"
echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
echo "AWS_STORAGE_BUCKET_NAME=$BUCKET_NAME"
echo "AWS_S3_REGION_NAME=$REGION"
echo "----------------------------------------"
echo ""
echo "EC2 접속:"
echo "ssh -i ${PROJECT_NAME}-key.pem ubuntu@$ELASTIC_IP"
