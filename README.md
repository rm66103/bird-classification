## Project Description

### **Technical Requirements**

* **Python Version**: 3.10.0
* **Cloud Storage**: AWS S3
* **Data Source**: Xeno-canto Public API
* **Key Dependencies**: 
  * `requests` - API interactions
  * `boto3` - AWS S3 integration (for data storage)
* **Development Environment**: 
  * **Cursor IDE** - Primary development environment (agent-specific files are present for Cursor AI assistance)
  * **Jupyter Notebooks** - For experimentation and analysis

**Note**: This project is developed using **Cursor IDE** as the primary development environment. Agent-specific instructions are provided via the `.cursor/rules/` directory (the current Cursor convention), which contains rule files (`.mdc`) that guide the AI assistant. These files include instructions such as pyenv activation requirements and other project-specific guidelines.

### **AWS S3 Setup**

This project uses **AWS S3** for storing all audio recordings and metadata. The S3 bucket serves as the canonical storage layer for the entire dataset.

#### **S3 Bucket Configuration**

**Bucket Name**: `bird-classification-data` (or configure your own bucket name)

**S3 Path Structure:**
```
s3://bird-classification-data/
  ├── raw-audio/
  │   ├── northern_cardinal/
  │   │   ├── {recording_id}.mp3
  │   │   └── ...
  │   ├── carolina_wren/
  │   │   └── ...
  │   └── ...
  └── metadata/
      ├── recordings_metadata.csv
      └── recordings_metadata.json
```

#### **AWS Credentials Setup**

1. **Create an AWS Account** (if you don't have one):
   - Sign up at [aws.amazon.com](https://aws.amazon.com)
   - Complete account verification

2. **Create an IAM User** (recommended for programmatic access):
   - Go to AWS IAM Console → Users → Add users
   - Create a user with programmatic access
   - Attach policy: `AmazonS3FullAccess` (or create a custom policy with S3 read/write permissions)
   - Save the Access Key ID and Secret Access Key

3. **Create S3 Bucket**:
   - Go to AWS S3 Console → Create bucket
   - Choose a unique bucket name (e.g., `bird-classification-data`)
   - Select your preferred AWS region (e.g., `us-east-1`)
   - Configure bucket settings (versioning, encryption, etc.) as needed
   - **Note**: Bucket names must be globally unique across all AWS accounts

4. **Configure Environment Variables**:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Add your AWS credentials and bucket configuration:
     ```
     AWS_ACCESS_KEY_ID=your_access_key_id_here
     AWS_SECRET_ACCESS_KEY=your_secret_access_key_here
     AWS_REGION=us-east-1
     S3_BUCKET_NAME=bird-classification-data
     ```
   - Also add your Xeno-canto API key:
     ```
     XENO_CANTO_API_KEY=your_xeno_canto_api_key_here
     ```

5. **Verify Setup**:
   - Ensure `.env` is in `.gitignore` (never commit credentials)
   - Test S3 connectivity by running the data acquisition notebook

**Security Best Practices:**
- Never commit `.env` file to version control
- Use IAM users with least-privilege access (not root account)
- Consider using AWS IAM roles if running on EC2/ECS
- Rotate access keys periodically

### **Dataset Selection and Acquisition**

This project uses **publicly available bird call recordings from the Xeno-canto database**, a large, community-maintained repository of labeled bird vocalizations from around the world.

All audio data is programmatically retrieved using the **Xeno-canto public API**:  
[https://xeno-canto.org/explore/api](https://xeno-canto.org/explore/api)

The API provides structured metadata for each recording, including:

* Species scientific name  
* Common name  
* Recording quality rating  
* Country / region  
* Audio file URL (typically MP3)  
* Additional contextual metadata (date, length, background species, etc.)

### **Dataset Scope**

The current dataset focuses on **8 common Georgia bird species**:

* Northern Cardinal (*Cardinalis cardinalis*)
* Carolina Wren (*Thryothorus ludovicianus*)
* Blue Jay (*Cyanocitta cristata*)
* American Robin (*Turdus migratorius*)
* Mourning Dove (*Zenaida macroura*)
* Tufted Titmouse (*Baeolophus bicolor*)
* Carolina Chickadee (*Poecile carolinensis*)
* Eastern Bluebird (*Sialia sialis*)

To keep the project focused, cost-effective, and fast to iterate on, the dataset is intentionally scoped:

* **8 bird species**  
* **\~50–100 recordings per species**  
* Total dataset size: **\~400–800 audio files**

This size is large enough to demonstrate a real multi-class classification pipeline, while remaining small enough to:

* Train models quickly  
* Avoid excessive AWS compute costs  
* Enable rapid experimentation and iteration

Species selection can be:

* Random  
* Based on geographic region (e.g., North American birds)  
* Personally meaningful (e.g., birds commonly found locally)

### **Data Ingestion Pipeline**

All audio files and metadata are stored in **AWS S3**, which serves as the system of record for the project.

**Workflow:**

1. Query the Xeno-canto API for target species.  
2. Download recording metadata (JSON).  
3. Download corresponding audio files (MP3).  
4. Upload raw audio files to S3.  
5. Persist metadata as CSV/JSON in S3 for downstream processing.

This approach ensures:

* Reproducibility  
* Clear separation between raw data and derived artifacts  
* Easy integration with AWS SageMaker and batch processing jobs

### **Metadata Handling**

Metadata returned from the Xeno-canto API is normalized and stored alongside the audio files. A structured dataset (e.g., CSV) is created with fields such as:

* `recording_id`  
* `species_scientific_name`  
* `species_common_name`  
* `audio_s3_uri`  
* `recording_quality`  
* `duration_seconds`  
* `location`

This metadata is loaded using **pandas** and acts as the authoritative source for:

* Label assignment  
* Train / validation splits  
* Dataset filtering (e.g., removing low-quality recordings)

### **Key Design Decisions**

* **Xeno-canto is the only data source** (no Kaggle, no mixed datasets).  
* **AWS S3 is the canonical storage layer** for all raw and processed data.  
* Audio labeling is inherited directly from Xeno-canto metadata (no manual labeling).  
* Dataset size is deliberately constrained to support low-cost experimentation.

