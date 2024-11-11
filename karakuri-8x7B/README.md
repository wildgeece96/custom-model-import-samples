# KARAKURI LM 8x7B Chat v0.1 

![gif](./docs/karakuri-streamlit-app.gif)

ここのフォルダでは、KARAKURI LM 8x7B Chat v0.1 を Custom Model Import して使う例を示しています。  

## 実行環境

- SageMaker Studio Code Editor (Image: SageMaker Distribution 2.0.0)
- ストレージ: 512GB

必要な権限
- IAM Role の作成・ポリシーのアタッチをする権限
- モデルの重みを格納する S3 バケットへ書き込み権限（AmazonS3FullAccess など）
- Bedrock への FullAccess（AmazonBedrockFullAccess など）

IAM の作成・ポリシーアタッチに関するポリシー例
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"iam:CreatePolicy",
				"iam:CreateRole",
				"iam:AttachRolePolicy"
			],
			"Resource": [
				"arn:aws:iam::<aws_account_id>:role/bedrock-cmi*",
				"arn:aws:iam::<aws_account_id>:policy/bedrock-cmi*"
			]
		}
	]
}
```

## setup

git lfs のインストール
```sh
# Ubuntu/Debian の場合
sudo apt-get install git-lfs
# MacOS の場合
brew install git-lfs
```

Python の仮想環境の構築
```sh
python -m venv .venv 
source .venv/bin/activate
pip install -r requirements.txt
```

他に準備するリソース
- データをアップロードするための S3 バケット（Custom Model Import を実施するリージョンと同じにしてください）



## 手順

### Model ダウンロードと Model Import. 

モデルを HuggingFace hub からダンロードし、S3 へアップロードします。  
モデルサイズが大きいため、１時間以上かかります。  
```sh
# 必要情報を指示に従って入力する
./download.sh
```

import したモデルの ARN がメッセージに表示されるので、それをメモしておく。  


### Import したモデルの使用

シンプルに呼び出す

```sh
python call_imported_model.py --model-arn <メモした ARN>
```

Streamlit でのサンプルアプリのホスト

```sh
streamlit run app.py -- --model-arn <メモした ARN>
```
Code Editor の場合、pinggy と呼ばれるサービスを利用することでホストされた UI を確かめることができます。  
うまくいけば HTTP/HTTPS から始まる URL が表示されます。https:// から始まる URL をコピーし、ウェブブラウザの別タブを開き、URL バーに貼り付けて移動してください。  
```sh
ssh -p 443 -R0:localhost:8501 a.pinggy.io
```


