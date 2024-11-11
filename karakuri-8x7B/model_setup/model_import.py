"""S3 にアップロードした重みを使って Bedrock 上にモデルを import する
"""
import argparse
import logging
import os
import time
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BedrockModelImporter:
    def __init__(self, model_id, bucket_name, region_name='us-west-2', s3_prefix=None):
        """
        :param model_id: HuggingFace のモデル ID (例: 'karakuri-ai/karakuri-lm-8x7b-chat-v0.1')
        :param bucket_name: S3 バケット名
        :param region_name: AWS リージョン名
        :param s3_prefix: S3 プレフィックス（指定がない場合はモデル名から生成）
        """
        self.model_id = model_id
        self.repo_name = self._extract_repo_name(model_id)
        
        self.config = {
            'region_name': region_name,
            'bucket_name': bucket_name,
            's3_prefix': s3_prefix or self.repo_name,
            'role_name': f"bedrock-cmi-{self.repo_name}-import-role",
            'policy_name': f"bedrock-cmi-{self.repo_name}-s3-policy",
            'job_name': f"{self.repo_name}-import-job-{int(time.time())}",
            'model_name': self.repo_name
        }

        self.iam = boto3.client('iam', region_name=self.config['region_name'])
        self.bedrock = boto3.client('bedrock', region_name=self.config['region_name'])
        
        logger.info(f"Initialized with configuration: {self.config}")

    def _extract_repo_name(self, model_id):
        """モデルIDからリポジトリ名を抽出して正規化"""
        # スラッシュで分割して最後の部分を取得
        repo_name = model_id.split('/')[-1]
        # 特殊文字を置換
        repo_name = repo_name.replace('.', '-').lower()
        return repo_name

    def create_iam_role(self):
        """IAMロールとポリシーの作成"""
        try:
            # ロールの作成
            logger.info(f"Creating IAM role: {self.config['role_name']}")
            role_response = self.iam.create_role(
                RoleName=self.config['role_name'],
                AssumeRolePolicyDocument='''{
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }]
                }'''
            )
            
            # S3アクセス用ポリシーの作成
            logger.info(f"Creating IAM policy: {self.config['policy_name']}")
            policy_response = self.iam.create_policy(
                PolicyName=self.config['policy_name'],
                PolicyDocument=f'''{{
                    "Version": "2012-10-17",
                    "Statement": [{{
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            "arn:aws:s3:::{self.config['bucket_name']}",
                            "arn:aws:s3:::{self.config['bucket_name']}/*"
                        ]
                    }}]
                }}'''
            )

            # ポリシーをロールにアタッチ
            logger.info("Attaching policy to role...")
            self.iam.attach_role_policy(
                RoleName=self.config['role_name'],
                PolicyArn=policy_response['Policy']['Arn']
            )

            # IAMロールが有効になるまで待機
            logger.info("Waiting for IAM role to be ready...")
            time.sleep(10)

            return role_response['Role']['Arn']

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                logger.info("IAM role already exists, retrieving ARN...")
                role = self.iam.get_role(RoleName=self.config['role_name'])
                return role['Role']['Arn']
            else:
                logger.error(f"Error creating IAM role: {str(e)}")
                raise

    def import_model(self, role_arn: str):
        """Bedrockへのモデルインポート開始"""
        try:
            s3_uri = f"s3://{self.config['bucket_name']}/{self.config['s3_prefix']}"
            logger.info(f"Starting model import from {s3_uri}")
            
            response = self.bedrock.create_model_import_job(
                jobName=self.config['job_name'],
                importedModelName=self.config['model_name'],
                roleArn=role_arn,
                modelDataSource={
                    "s3DataSource": {
                        "s3Uri": s3_uri
                    }
                }
            )
            return response['jobArn']
            
        except ClientError as e:
            logger.error(f"Error starting model import: {str(e)}")
            raise

    def check_import_status(self, job_arn: str) -> str:
        """インポートジョブのステータスチェック"""
        try:
            response = self.bedrock.get_model_import_job(
                jobIdentifier=job_arn
            )
            return response['status']
        except ClientError as e:
            logger.error(f"Error checking import status: {str(e)}")
            raise

    def get_imported_model_arn(self, job_arn: str) -> str:
        """インポートジョブのステータスチェック"""
        try:
            response = self.bedrock.get_model_import_job(
                jobIdentifier=job_arn
            )
            return response['importedModelArn']
        except ClientError as e:
            logger.error(f"Error checking import status: {str(e)}")
            raise

def parse_arguments():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(
        description='Download a model from HuggingFace and upload it to S3'
    )
    
    parser.add_argument(
        '--model-id',
        type=str,
        default="karakuri-ai/karakuri-lm-8x7b-chat-v0.1",
        help='HuggingFace model ID (default: karakuri-ai/karakuri-lm-8x7b-chat-v0.1)'
    )
    
    parser.add_argument(
        '--bucket',
        type=str,
        required=True,
        help='S3 bucket name for upload'
    )

    parser.add_argument(
        '--region',
        type=str,
        default='us-west-2',
        help='region to import model and S3 location.'
    )
    
    
    parser.add_argument(
        '--s3-prefix',
        type=str,
        default="karakuri-model",
        help='S3 prefix for uploaded files (default: karakuri-model)'
    )
    
    
    return parser.parse_args()


def main():
    args = parse_arguments()

    importer = BedrockModelImporter(
        model_id=args.model_id,
        bucket_name=args.bucket,
        region_name=args.region,
        s3_prefix=args.s3_prefix
    )

    try:
        # Step 1: IAMロールの作成
        logger.info("Step 1: Creating IAM role and policy...")
        role_arn = importer.create_iam_role()
        logger.info(f"Role ARN: {role_arn}")

        # Step 2: モデルインポートの開始
        logger.info("Step 2: Starting model import...")
        job_arn = importer.import_model(role_arn)
        logger.info(f"Import job ARN: {job_arn}")

        # Step 3: インポート完了を待機
        logger.info("Step 3: Waiting for import to complete...")
        while True:
            status = importer.check_import_status(job_arn)
            logger.info(f"Import status: {status}")
            
            if status == 'Completed':
                imported_model_arn = importer.get_imported_model_arn(job_arn)
                logger.info("Model import completed successfully!")
                logger.info("Imported Model ARN: ", )
                break
            elif status in ['Failed', 'Stopped']:
                raise Exception(f"Import failed with status: {status}")
            
            time.sleep(60)

    except Exception as e:
        logger.error(f"Error in import process: {str(e)}")
        raise

if __name__ == "__main__":
    main()
