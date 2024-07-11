import pandas as pd

df = pd.read_excel(r'C:\Users\KTHD\Downloads\안구건조증 설계 ing.xlsx', sheet_name='solution_package')

df = df.set_index(['팩No.'])

idx = "팩1"

package_name = df.loc[idx]['패키지명']
package_gusang = df.loc[idx]['패키지 구성']
selling_price = df.loc[idx]['판매가격']

print(df.columns)

print(df.loc["팩3"]['추천 사유'])

