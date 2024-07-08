import os

# 파일이 저장된 디렉토리 경로
directory = r'C:\Users\djmin\Downloads\새 폴더\증상솔루션\templates'

# 현재 디렉토리로 변경 (파일이 있는 디렉토리로 변경)
os.chdir(directory)

# 파일 이름을 변경하는 함수
def rename_files():
    for i in range(2, 11):
        old_name = f'question1 copy {i}.html'
        new_name = f'question{i}.html'
        if os.path.exists(old_name):
            os.rename(old_name, new_name)
            print(f'Renamed: {old_name} to {new_name}')
        else:
            print(f'File not found: {old_name}')

# 파일 이름 변경 실행
rename_files()
