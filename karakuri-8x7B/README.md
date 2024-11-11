# KARAKURI LM 8x7B Chat v0.1 

![gif](./docs/karakuri-streamlit-app.gif)

ここのフォルダでは、KARAKURI LM 8x7B Chat v0.1 を Custom Model Import して使う例を示しています。  

## 実行環境

- SageMaker Studio Code Editor (Image: SageMaker Distribution 2.0.0)
- ストレージ: 512GB

必要な権限
- IAM Role の作成・ポリシーのアタッチ
- モデルの重みを格納する S3 バケットへの FullAccess
- Bedrock への FullAccess

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





