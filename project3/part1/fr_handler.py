__copyright__   = "Copyright 2024, VISA Lab"
__license__     = "MIT"

import warnings
warnings.filterwarnings("ignore", message=".*cpuinfo.*failed to parse.*")

import os
import cv2
import imutils
import json
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image, ImageDraw, ImageFont
from shutil import rmtree
import numpy as np
import torch
import logging
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embedding conversion
s3 = boto3.client('s3')


def face_recognition_function(key_path):
    logger.info("Starting face recognition process.")
    dataptbucket = 'myawsbucket123456778'
    download_path = '/tmp/data.pt'

    try:
        logger.info(f"Downloading data.pt file from S3 bucket: {dataptbucket}")
        s3.download_file(dataptbucket, 'data.pt', download_path)
    except Exception as e:
        logger.error(f"Error downloading data.pt from S3: {e}")
        raise e

    # Face extraction
    logger.info(f"Loading image from path: {key_path}")
    img = cv2.imread(key_path, cv2.IMREAD_COLOR)
    if img is None:
        logger.error(f"Failed to read image from path: {key_path}")
        return

    logger.info("Detecting faces in the image.")
    boxes, _ = mtcnn.detect(img)

    # Face recognition
    key = os.path.splitext(os.path.basename(key_path))[0].split(".")[0]
    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    logger.info("Extracting face and probabilities.")
    face, prob = mtcnn(img, return_prob=True, save_path=None)
    try:
        saved_data = torch.load(download_path)  # loading data.pt file
    except Exception as e:
        logger.error(f"Error loading data.pt file: {e}")
        raise e

    if face is not None:
        logger.info("Calculating embeddings for detected face.")
        emb = resnet(face.unsqueeze(0)).detach()
        embedding_list = saved_data[0]  # getting embedding data
        name_list = saved_data[1]  # getting list of names
        dist_list = []  # list of matched distances

        for idx, emb_db in enumerate(embedding_list):
            dist = torch.dist(emb, emb_db).item()
            dist_list.append(dist)
        idx_min = dist_list.index(min(dist_list))

        # Save the result name in a file
        result_name = name_list[idx_min]
        logger.info(f"Face matched with: {result_name}")
        with open("/tmp/" + key + ".txt", 'w+') as f:
            f.write(result_name)
        return result_name
    else:
        logger.warning("No face detected in the image.")
        return None


def handler(event, context):
    logger.info("Handler function triggered.")
    filename = event.get('image_file_name')
    bucket_name = event.get('bucket_name')

    if not filename or not bucket_name:
        logger.error("Event must include 'image_file_name' and 'bucket_name'.")
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid input: Missing required parameters.')
        }

    logger.info(f"Processing file: {filename} from bucket: {bucket_name}")
    download_path = '/tmp/' + filename

    try:
        logger.info(f"Downloading file {filename} from bucket {bucket_name} to {download_path}.")
        s3.download_file(bucket_name, filename, download_path)
    except Exception as e:
        logger.error(f"Error downloading file from S3: {e}")
        raise e

    result_name = face_recognition_function(download_path)
    if result_name is None:
        return {
            'statusCode': 200,
            'body': json.dumps('No face detected in the image.')
        }

    output_bucket = "1230704334-output"
    out_file_name = filename.split('.')[0] + '.txt'
    out_file_path = '/tmp/' + out_file_name

    try:
        logger.info(f"Uploading result file {out_file_name} to bucket {output_bucket}.")
        with open(out_file_path, 'rb') as file:
            s3.upload_fileobj(file, output_bucket, out_file_name)
    except Exception as e:
        logger.error(f"Error uploading result file to S3: {e}")
        raise e

    logger.info("Handler function completed successfully.")
    return {
        'statusCode': 200,
        'body': json.dumps('Output generated successfully...')
    }