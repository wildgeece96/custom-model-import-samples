#!/bin/bash

# Color settings
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_MODEL_ID="karakuri-ai/karakuri-lm-8x7b-chat-v0.1"
DEFAULT_BUCKET_PREFIX="karakuri-model"
DEFAULT_AWS_REGION="us-west-2"

# Display banner
echo -e "${BLUE}================================"
echo "Model Import Interactive Setup"
echo -e "================================${NC}"

# Region
echo -e "\n${GREEN}Please enter the region name"
echo -e "Default: ${DEFAULT_AWS_REGION}${NC}"
read -p "> " AWS_REGION
AWS_REGION=${AWS_REGION:-$DEFAULT_AWS_REGION}

# Input S3 bucket name
while true; do
    echo -e "\n${GREEN}Please enter your S3 bucket name:${NC}"
    read -p "> " BUCKET_NAME
    
    if [ -z "$BUCKET_NAME" ]; then
        echo -e "${RED}Bucket name is required.${NC}"
        continue
    fi
    
    # Verify bucket existence
    if aws s3 ls "s3://${BUCKET_NAME}" >/dev/null 2>&1; then
        echo -e "${GREEN}Bucket verified: ${BUCKET_NAME}${NC}"
        break
    else
        echo -e "${RED}Bucket does not exist or no access permission: ${BUCKET_NAME}${NC}"
        read -p "Would you like to specify a different bucket? (y/n): " retry
        if [ "$retry" != "y" ]; then
            echo -e "${RED}Exiting script${NC}"
            exit 1
        fi
    fi
done

# Input model ID
echo -e "\n${GREEN}Please enter the HuggingFace model ID"
echo -e "Default: ${DEFAULT_MODEL_ID}${NC}"
read -p "> " MODEL_ID
MODEL_ID=${MODEL_ID:-$DEFAULT_MODEL_ID}

# Input S3 prefix
echo -e "\n${GREEN}Please enter the S3 prefix"
echo -e "Default: ${DEFAULT_BUCKET_PREFIX}${NC}"
read -p "> " BUCKET_PREFIX
BUCKET_PREFIX=${BUCKET_PREFIX:-$DEFAULT_BUCKET_PREFIX}

# Confirmation
echo -e "\n${BLUE}=== Configuration Summary ===${NC}"
echo "S3 Bucket Name: $BUCKET_NAME"
echo "Model ID: $MODEL_ID"
echo "S3 Prefix: $BUCKET_PREFIX"

read -p "Proceed with these settings? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo -e "${RED}Script cancelled${NC}"
    exit 1
fi

# Set environment variables
export MODEL_BUCKET_NAME="$BUCKET_NAME"
export MODEL_ID="$MODEL_ID"
export MODEL_S3_PREFIX="$BUCKET_PREFIX"
export AWS_REGION="$AWS_REGION"

# Display environment variables
echo -e "\n${BLUE}Environment variables set:${NC}"
echo "MODEL_BUCKET_NAME=$MODEL_BUCKET_NAME"
echo "MODEL_ID=$MODEL_ID"
echo "MODEL_S3_PREFIX=$MODEL_S3_PREFIX"
echo "AWS_REGION=$AWS_REGION"

# Execute Python script
echo -e "\n${BLUE}Executing Model download python script..${NC}"
python model_setup/download_upload_model.py \
    --bucket "$MODEL_BUCKET_NAME" \
    --model-id "$MODEL_ID" \
    --s3-prefix "$MODEL_S3_PREFIX" \
    --local-path "models/$MODEL_ID"


echo -e "\n${BLUE}Executing start Model Import Job on Berock python script...${NC}"
python model_setup/model_import.py \
    --bucket "$MODEL_BUCKET_NAME" \
    --model-id "$MODEL_ID" \
    --s3-prefix "$MODEL_S3_PREFIX" \
    --region "$AWS_REGION"

# Check execution result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Script completed successfully${NC}"
else
    echo -e "${RED}An error occurred during script execution${NC}"
fi


