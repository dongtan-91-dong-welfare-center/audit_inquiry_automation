# Tesseract OCR 설치 가이드
## 개요
이미지의 텍스트를 추출하기 위해서는 Tesseract OCR이 필수적으로 설치되어 있어야 합니다.

> ! IMPORTANT
Tesseract OCR은 Google에서 개발한 오픈소스 OCR 엔진으로, 로컬 환경에서 무료로 사용할 수 있습니다.

### Windows 설치 방법
#### 1. Tesseract OCR 다운로드
공식 Windows 인스톨러를 다운로드합니다.

다운로드 링크: [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
추천 버전: tesseract-ocr-w64-setup-5.5.0.20241111.exe (64비트 Windows)

#### 2. 설치 실행
다운로드한 .exe 파일을 실행합니다.
Please select a language.는 english를 선택합니다.
'install for anyone using this computer' 선택합니다.
"Additional script data (download)" 옵션에서 다음 언어를 선택합니다.
- ✅ Hangul script
- ✅ Hangul vertical script
"Additional language data (download)" 옵션에서 다음 언어를 선택합니다.
- ✅ Korean

기본 설치 경로 사용 (권장): `C:\Program Files\Tesseract-OCR`

#### 3. 환경 변수 설정 (중요!)
Tesseract를 어디서든 사용할 수 있도록 PATH 환경 변수에 추가합니다

1. Windows 검색에서 "환경 변수" 검색
2. 환경 변수 버튼 클릭
3. 시스템 변수에서 Path 선택 후 편집
4. 새로 만들기를 클릭하고 Tesseract 설치 경로(C:\Program Files\Tesseract-OCR) 추가
5. 확인을 클릭하여 모든 창 닫기

#### 4. 설치 확인
새 PowerShell 또는 명령 프롬프트를 열고 다음 명령어를 실행합니다:

``` powershell
tesseract --version
```

```aiignore
tesseract v5.5.0.20241111
 leptonica-1.85.0
  libgif 5.2.2 : libjpeg 8d (libjpeg-turbo 3.0.4) : libpng 1.6.44 : libtiff 4.7.0 : zlib 1.3.1 : libwebp 1.4.0 : libopenjp2 2.5.2
 Found AVX2
 Found AVX
 Found FMA
 Found SSE4.1
 Found libarchive 3.7.7 zlib/1.3.1 liblzma/5.6.3 bz2lib/1.0.8 liblz4/1.10.0 libzstd/1.5.6
 Found libcurl/8.11.0 Schannel zlib/1.3.1 brotli/1.1.0 zstd/1.5.6 libidn2/2.3.7 libpsl/0.21.5 libssh2/1.11.0
```

#### 5. 한국어 언어 팩 확인
한국어 데이터가 설치되어 있는지 확인

```powershell
tesseract --list-langs
```

```aiignore
List of available languages in "C:\Program Files\Tesseract-OCR/tessdata/" (5):
eng
kor
osd
script\Hangul
script\Hangul_vert
```

#### 6. 참고
공식 문서: https://tesseract-ocr.github.io/
GitHub: https://github.com/tesseract-ocr/tesseract
한국어 학습 데이터: https://github.com/tesseract-ocr/tessdata
