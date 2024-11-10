# Project 3: Serverless Video-Based Face Recognition Using AWS Lambda (PaaS)

This project implements a serverless video analysis pipeline using AWS Lambda (PaaS), S3, and supporting AWS services. It offers facial recognition as a cloud service that processes `.mp4` videos by splitting, analyzing frames, and identifying faces through a ResNet-based model. The system is fully elastic and processes videos via an event-driven architecture without the need to manage any servers.

---

## 🧠 Overview

The application is structured as a **multi-stage pipeline** powered by AWS Lambda and S3. It includes:

- **Video Upload** by user to trigger processing
- **Video Splitting Function** to extract frames (GoP)
- **Face Recognition Function** to identify known faces
- **S3 Buckets** to manage input, intermediate, and output data

This pipeline handles videos at scale using asynchronous invocation and manages intermediate outputs cleanly through decoupled Lambda stages.

---

## 🎯 Functional Breakdown

### ✅ Part 1: Video Splitting

- **Trigger**: Upload to `<ASU_ID>-input` S3 bucket
- **Lambda Function**: `video-splitting`
- **Functionality**:
  - Extracts frames (GoP) using FFmpeg:  
    `ffmpeg -ss 0 -r 1 -i input.mp4 -vf fps=1/10 -start_number 0 -vframes 10 output-%02d.jpg`
  - Stores extracted frames in a folder named after the video (e.g., `test_00/`) inside the `<ASU_ID>-stage-1` bucket

---

### ✅ Part 2: Face Recognition

- **Trigger**: Asynchronous invocation by the `video-splitting` Lambda function
- **Lambda Function**: `face-recognition`
- **Functionality**:
  - Takes the frame (one per video in Part 2) from `<ASU_ID>-stage-1`
  - Detects and embeds facial features using ResNet-34
  - Compares embeddings with a reference dataset (`data.pt`)
  - Writes the identified person’s name into a `.txt` file in the `<ASU_ID>-output` bucket

---

## 🗂 Buckets & Naming Convention

| Bucket Purpose     | Name Format             |
|--------------------|--------------------------|
| Input Videos       | `<ASU_ID>-input`         |
| Intermediate Frames| `<ASU_ID>-stage-1`       |
| Output Labels      | `<ASU_ID>-output`        |

Uploaded videos → trigger video-splitting → which triggers face-recognition → saves name

---

## 🧪 Testing & Grading

- Graded using AWS Lambda logs and a **workload generator** with 100 `.mp4` test videos
- Evaluated on:
  - Correct Lambda setup and invocation
  - S3 naming, folder structure, and output format
  - Accuracy of face recognition results
  - End-to-end latency (< 300 sec preferred for 100 videos)
  - Lambda concurrency and function duration

---

## 🛠 Technologies Used

- AWS Lambda (PaaS)
- AWS S3
- OpenCV, Torch, TorchVision (CPU-based)
- FFmpeg
- Docker (for containerized Lambda deployment of face-recognition function)

---

## ✅ Deployment Notes

- Region: `us-east-1`
- All Lambda functions use IAM roles with:
  - `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `lambda:InvokeFunction`, `cloudwatch:GetMetricData`
- Grading IAM user must be shared with appropriate permissions
