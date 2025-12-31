"""
CLI(Command Line Interface) 실행기

[모듈 개요]
웹 브라우저를 켜지 않고, 터미널(검은 화면)에서 명령어로 프로그램을 실행할 때 사용합니다.
서버에서 자동으로 대량의 파일을 처리하거나(배치 작업),
개발자가 빠르게 테스트를 돌려볼 때 유용합니다.

[사용 라이브러리]
- click: 파이썬 함수를 예쁜 명령줄 도구로 만들어주는 라이브러리입니다.
         (사용자가 '--input' 같은 옵션을 쉽게 넣을 수 있게 도와줍니다.)
"""

import click

# 앞서 우리가 정성껏 만든 '지휘관' 모듈을 데려옵니다.
# (이 연결 고리가 있어야 명령을 받았을 때 실제로 일을 시킬 수 있습니다.)
from .processor import process_pdf_to_excel


@click.command()
# [옵션 설정]
# 사용자가 입력해야 할 명령어 옵션들을 정의합니다.
# required=True는 이 옵션이 없으면 실행을 거부하겠다는 뜻입니다.
@click.option('--input', type=click.Path(exists=True), required=True, help='처리할 원본 PDF 파일의 경로입니다.')
@click.option('--output', type=click.Path(), required=True, help='결과 엑셀 파일을 저장할 경로입니다.')
def main(input, output):
    """
    [명령어 진입점]
    터미널에서 이 스크립트를 실행하면 가장 먼저 호출되는 함수입니다.

    사용 예시:
    python -m src.cli --input data/sample.pdf --output result/output.xlsx
    """

    # 1. 사용자에게 시작을 알립니다.
    click.echo(f"🚀 작업을 시작합니다...")
    click.echo(f"- 입력 파일: {input}")
    click.echo(f"- 출력 경로: {output}")

    try:
        # 2. [핵심 로직 연결]
        # processor.py에 있는 '지휘관' 함수를 호출하여 실제 작업을 수행합니다.
        # 여기서 반환값(count)은 처리된 표의 개수입니다.
        count = process_pdf_to_excel(input, output)

        # 3. 결과 보고
        if count > 0:
            click.echo(f"✅ 성공! 총 {count}개의 표를 추출하여 저장했습니다.")
        else:
            click.echo("⚠️ 알림: 추출된 표가 없습니다.")

    except Exception as e:
        # 작업 중 에러가 발생하면 빨간색 글씨(err=True)로 알려줍니다.
        click.echo(f"❌ 오류 발생: {str(e)}", err=True)


# 이 파일이 직접 실행될 때만 main() 함수를 호출합니다.
if __name__ == '__main__':
    main()