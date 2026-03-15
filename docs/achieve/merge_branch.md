1. 내가 개발하는 브랜치로 이동한다.(현재 같은 경우는 tess)
2. 원격 브랜치 최신화(git fetch origin)
3. 새로운 테스트 브랜치를 딴다.(git checkout -b {새로 만드는 브랜치의 이름} tess)
   - 이 브랜치는 원격에 올리지 않고 로컬에서만 사용한다.
   - 어차피 합치는 건 dev에서 한다. 그래서 이 테스트 브랜치는 원격에 올릴 필요가 없다.
4. 새로운 브랜치와 이규석의 기능 브랜치를 합친다.(git merge origin/feature/preprocessor)
