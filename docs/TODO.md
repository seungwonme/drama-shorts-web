# TODO

- [x] 선택적으로 광고 제품 뿐만 아니라 줄거리/대본도 받기
- [x] 영상 글씨 제거
- [x] 실행마다 영상 덮어쓰기 X -> 폴더를 만들어서 영상 저장
- [x] 인물 일관성 유지
- [x] 프롬프트 구조 확립
- [x] 라스트 씬 이미지 정해져 있고 효과음과 함께
- [x] Django Admin
- [x] 제품 이미지 업로드 기능
- [x] 제품 링크 안들어가는 문제 해결
- [x] S3에 에셋 ID별로 구분하여 정리
- [x] assets 폴더에 있는 라스트 씬 이미지, 효과음 업로드 기능
- [x] 단계별로 재작업 기능 추가
  - nano banana: 첫번째 씬의 첫 번째 프레임 다시 제작하기
  - Veo3.1: 첫 번째 씬 다시 제작하기
  - nano banana: 첫번째 씬의 마지막 프레임 다시 제작하기
  - Veo3.1: 두 번째 씬 다시 제작하기
  - last_cta: 이미지, 효과음 다시 업로드하기
  - ffmpeg: 첫 번째 씬 + 두 번째 씬 + last_cta 합치기
  - [ ] 에러 수정
- [ ] ffmpeg 자막 기능 추가
  - 스크립트 기반 영상 뽑아서 스크립트 자막 달기
  - STT -> 구조는 우선 순위로 두되, 프롬프트로 적었던 대본을 LLM에게 검증하는 로직을 추가하여 타임 스탬프 제대로 확인
- [ ] 문제
  - [ ] 인물의 대사가 바뀌는 문제
  - [ ] 상품 이미지 주소를 넣었는데 영상에 안 들어가는 문제
    - [ ] https://d2igltf4n6ib86.cloudfront.net/characters/0be0386c-7c7b-4048-96ca-c9902ec4901f/a2040c83-1cd8-4863-b0ae-659174439ee5.jpeg 영양제
  - [ ] 센서티브 에러 우회 로직 생성하개
    ```sh
    Failed to generate video: {'code': 8, 'message': 'The service is currently experiencing high load and cannot process your request. Please try again later. Operation ID: b3aac92b-794e-419d-a636-64669a59160f.'}
    ```
  - [ ] 한 노드에서 너무 많은 작업을 처리하는 문제

---

## 드라마 형식 쇼츠 개선점

- [x] 핵심 규칙을 템플릿화하여 선택할 수 있도록 제공 -> 기본 형식은 B급 막장 드라마 형식으로 변경
- [ ] 전체적인 프롬프트 고도화
  - [ ] 현재 시퀀스 2초씩 4개 고정되어있는데 화자 단위로 시퀀스를 분리 (시퀀스 설명 세분화) (e.g. 00:00~01:30 "저기요" 캐릭터 A -> 01:30~02:00 "어?" 캐릭터 B ...)
  - [ ] 2번째 씬 생성 프롬프트에 이전 씬에 대한 설명 추가
  - [ ] 캐릭터 성별 및 묘사 디테일 추가
- [ ] 대본 제작과 이미지/영상 제작 프롬프트에 이 쇼츠에 대한 전체적인 맥락을 넣기
- [ ] 시퀀스를 4개에서 3개로 줄인다. (시퀀스 길이 여유 두자)

### 롯데리아: 내일 시연하는 거는 '방구석여포 도발 + 롯데리아형 스토리콘텐츠' 3개만 할 것 같아요!! 요것만 작업해주셔도 충분할 것 같아요!!
외부인이 긁으면 -> 내부 관계자가 증명

### 고재영:
지금부터 NN일 안에 ~하겠습니다.

## 캐릭터 스토리 쇼츠

1. 캐릭터를 맘대로 넣을 수 있어야 한다.
2. 대본을 잘 인식시켜야 한다.

### 핵심:

- 등장 인물
- 여러 소스 (에란겔 배경, 후라이펜, 헬기) -> 스토리에 맞게 등장

## 관련 자료

- https://bbs.pubg.game.daum.net/gaia/do/pubg/competition/read?bbsId=PN001&articleId=4099&objCate1=223
- https://docs.google.com/spreadsheets/d/1W4EJudAGRk7_zkemVIOUtSz1BhwS9jRhD7HBma5_ZeA/edit?gid=431509896#gid=431509896
- https://docs.google.com/spreadsheets/d/1W4EJudAGRk7_zkemVIOUtSz1BhwS9jRhD7HBma5_ZeA/edit?gid=1355792315#gid=1355792315
- https://www.youtube.com/watch?v=k3GnHTPEgJI


치크 병아리 버전, 플레이어 버전
- 삐약삐약을 제외한 모든 것들은 효과음이 들어가야 한다.
- 프레임을 여러개 -> 영상 20초 이내
영상 스타일 커스터마이징 기능
스크립트 예시

매주 목요일 컨설팅 -> 3개 영상 필요

bfb96854-9b3b-4b7c-8fc8-74b20ce76ea4:a389576eae2d09aa43071fc21495e5d6

인풋
- 배경
- 인물(캐릭터)

요구사항
- 스크립트와 일치하는 영상 생성
- 중간에 텍스트를 최대한 제거
- 영상을 분할해서
