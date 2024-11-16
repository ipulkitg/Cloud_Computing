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


logger = logging.getLogger()
logger.setLevel(logging.INFO)



mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20) # initializing mtcnn for face detection
resnet = InceptionResnetV1(pretrained='vggface2').eval() # initializing resnet for face img to embeding conversion
s3 = boto3.client('s3')


def face_recognition_function(key_path):
    dataptbucket = 'facedatapt'
    download_path = '/tmp/data.pt'
    s3.download_file(dataptbucket, 'data.pt', download_path)
    # Face extraction
    img = cv2.imread(key_path, cv2.IMREAD_COLOR)
    boxes, _ = mtcnn.detect(img)

    # Face recognition
    key = os.path.splitext(os.path.basename(key_path))[0].split(".")[0]
    img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    face, prob = mtcnn(img, return_prob=True, save_path=None)
    saved_data = torch.load('/tmp/data.pt')  # loading data.pt file
    if face != None:
        emb = resnet(face.unsqueeze(0)).detach()  # detech is to make required gradient false
        embedding_list = saved_data[0]  # getting embedding data
        name_list = saved_data[1]  # getting list of names
        dist_list = []  # list of matched distances, minimum distance is used to identify the person
        for idx, emb_db in enumerate(embedding_list):
            dist = torch.dist(emb, emb_db).item()
            dist_list.append(dist)
        idx_min = dist_list.index(min(dist_list))

        # Save the result name in a file
        with open("/tmp/" + key + ".txt", 'w+') as f:
            f.write(name_list[idx_min])
        return name_list[idx_min]
    else:
        print(f"No face is detected")
    return


def handler(event, context):
    img_filename = event['image_file_name']
    src_bucket_name = event['bucket_name']
    download_path = '/tmp/' + img_filename
    s3.download_file(src_bucket_name, img_filename, download_path)
    face_recognition_function(download_path)
    output_bucket_name = "1230704334-output"
    out_file_name = img_filename.split('.')[0] + '.txt'
    out_file_path = '/tmp/' + out_file_name 
    with open(out_file_path, 'rb') as file:
        s3.upload_fileobj(file, output_bucket_name, out_file_name)
    return {
        'statusCode': 200,
        'body': json.dumps('Output generated successfully...')
    }