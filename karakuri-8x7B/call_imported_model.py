import argparse
import json
import logging
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BedrockModelInvoker:
    def __init__(self, config):
        """
        :param config: 設定値を含む辞書
        """
        # リトライ設定を含むboto3の設定
        boto3_config = Config(
            retries={
                'total_max_attempts': config['max_retries'],
                'mode': 'standard'
            }
        )
        
        # Bedrock Runtimeクライアントの初期化
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=config['region_name'],
            config=boto3_config
        )
        
        self.model_arn = config['model_arn']

    def invoke_model(self, prompt, max_tokens=100, temperature=0.7):
        """
        モデルを呼び出して推論を実行
        
        :param prompt: 入力プロンプト
        :param max_tokens: 生成する最大トークン数
        :param temperature: 生成の多様性（0-1）
        :return: モデルの応答
        """
        try:
            # リクエストボディの作成
            request_body = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # モデルの呼び出し
            logger.info(f"Invoking model with prompt: {prompt[:100]}...")  # プロンプトの先頭100文字のみログ出力
            start_time = time.time()
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_arn,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            end_time = time.time()
            # レスポンスの解析
            response_body = json.loads(response['body'].read().decode('utf-8'))
            logger.info(f"Response time is {end_time - start_time:.3f} sec")
            return response_body

        except ClientError as e:
            if e.response['Error']['Code'] == 'ModelNotReadyException':
                logger.warning("Model is not ready yet. Retry will be triggered automatically.")
                raise
            else:
                logger.error(f"Error invoking model: {str(e)}")
                raise

def parse_arguments():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(
        description='Download a model from HuggingFace and upload it to S3'
    )
    
    parser.add_argument(
        '--model-arn',
        type=str,
        required=True,
        help='Imported Model ARN'
    )

    parser.add_argument(
        '--region',
        type=str,
        default='us-west-2',
        help='Region of imported model.'
    )
    
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    config = {
        'region_name': args.region,  # モデルがインポートされているリージョン
        'model_arn': args.model_arn,
        'max_retries': 20  # リトライ回数
    }

    # テスト用のプロンプト
    test_prompts = [
        "[INST]あなたは AWS のエキスパートです。自己紹介をする時に、好きなサービスは Amazon Bedrock / Amazon SageMaker です。こんにちは。あなたの自己紹介をお願いできますか？[/INST]",
        "[INST]AIについて、あなたの意見を教えてください。[\INST]",
        "[INST]富士山の標高は何メートルですか？[\INST]",
        """[INST]あなたは、抽選を行うロボットです。下記リストの中から、ランダムな形で人を選び、それを出力してください。
        出力形式は下記のフォーマットのjsonでお願いします。jsonのみ出力してください。
        [LIST]
        - アマゾン太郎
        - ジーニアック時子
        [/LIST]
        [FORMAT]
        {
          "name": {
            "type": string,
            "description": "抽選された人の名前（フルネーム）"
          }
        }
        [/FORMAT]
        [/INST]
        """
    ]

    invoker = BedrockModelInvoker(config)

    logger.info(f"\n==== Started testing imported model. It may take few minutes to start first prompt because of the cold start. ===")
    # 各プロンプトでテスト
    for prompt in test_prompts:
        try:
            logger.info(f"\n=== Testing with prompt: {prompt} ===")
            
            response = invoker.invoke_model(
                prompt=prompt,
                max_tokens=256,
                temperature=0.7
            )
            
            logger.info("Response received:")
            logger.info(json.dumps(response, indent=2, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Error processing prompt: {str(e)}")
            continue

if __name__ == "__main__":
    main()
