# Wise CDK


## Installation

#### 1. Create the following resources in AWS, manually
```
 - A S3 bucket for the pipeline artifacts
 - A SSL certificate to each stack
 - A user with enough permissions to run CDK tasks 
```

#### 2. Install Docker, Docker compose and make 
This step is different acording your SO.
One you have all of this, exec the build command.

#### 3. Build CDK
```
make build
```

#### 4. Usage
```
$ make diff
$ make diff ARG=platform-api-production

---
$ make ls
$ make deploy
```

##### 5. AWS Vault alternative (optional)
 ```
$ npm install -g aws-cdk
$ virtualenv -p python3 env
$ source env/bin/activate
$ brew cask install aws-vault
```

After that you need to get AWS credentials and configure it

```bash
$ aws-vault add platform-api
Enter Access Key Id: ABDCDEFDASDASF
Enter Secret Key: %%%

# Execute a command (using temporary credentials)
$ aws-vault exec platform-api -- aws s3 ls

# open a browser window and login to the AWS Console
$ aws-vault login platform-api
```

### Considerations
```
This project is focused into deployments only.
all testing/linting and pre deploy taks should 
be realized in another engines, I recommend 
Github Actions.
```

### Setup Chamber on AWS

1. Create a KMS Key (Region could be different)
https://console.aws.amazon.com/kms/home?region=us-east-1#/kms/keys/create
2. Setup its alias as `parameter_store_key`
3. Copy its `Key ID` and use it as `KMS_KEY` var

### Requirements
1, setup domains
2. it needs a bucket called `platform-infra-artifact`
2. setup ssl certificates
3. create network VPC
4. get rout dns id zone value
5. How to get github access token
