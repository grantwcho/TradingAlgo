    # README #

Adaptive preference experiment.

### What is this repository for? ###

* Quick summary
* Version
* [Learn Markdown](https://bitbucket.org/tutorials/markdowndemo)

### How do I get set up? ###

Create python 3.7 virtualenv in _backend/_

    cd ${PROJECT}/RA/backend/ 
    python3.7 -m venv venv
    cd ${PROJECT}/RA/
    npm install

Install requirements

     pip install -r requirements.txt

    
Deployment instructions

    TODO

## Running App

You will need to open two terminals or IDEs one for front end and one for back end.

#### Backend


    cd ${PROJECT}/RA/backend/
    source venv/bin/activate
    flask run


#### Frontend

For local dev:

    cd ${PROJECT}/RA/
    REACT_APP_BACKEND_ENDPOINT=http://127.0.0.1:5000 npm start

For local dev with remote backend:

    cd ${PROJECT}/RA/
    REACT_APP_BACKEND_ENDPOINT=https://adpref-backend.wharton-research-programming.org npm start


## TO-DO

* Create deployment pipeline using Jenkins, AWS and Terraform
* Non-sequential user ids
* Offload results files to s3 or other non-transient storage
* Limit ip addresses
* Failure tolerant progress. If docker fails mid run, will user be able to continue?  

### Who do I talk to? ###

[Ryan Dew](mailto:ryandew@wharton.upenn.edu)# TradingAlgo
