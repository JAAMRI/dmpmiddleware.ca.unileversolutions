# import requests
from botocore.vendored import requests
# getting the current time
from datetime import datetime
# json format for working with the data
import json
# log for debugging
import logging

'''
SAM function to add submit user data from wyng dove campaign to the EPSILON database
When data is received, the function makes various calls 
Calls in Order:
    1. Get Transaction ID: This function is used to get the id for each call that would be made for this particular transaction.
    2. Get Vendor Authenticatio: This function verifies the vendor (Ustudio) and returns a JSON Object where we get both the Access and Refresh Token.
    3. Add Profile: This function creates a new profile for the current user which the function is submitting the data for. This returns a JSON Object containing the new profile Id.
    4. Add Survey Profile Responses: This function adds all survey profile responses for this particular profile that was just created, This returns a JSON Object containing Type 
    Processed if the call went through and Error if the call failed, and also returns the New Survey Profile Response Id if the call went through.
    5. Add Promotion Responses: This function adds the response for each data gotten from the client i.e How they found the wyng campaign e.g facebook,instagram,email, Do they optin
    to receive promotional emails from dove and unilever in general, Are they viewing the english or french campaign. For each of these various options they have a unique CampaignControlID
    and the date the record was created. This returns Type Processed if was successful.
    
At each function if there is an error, an exception is raised with the particular error which can be viewed in the log.
'''
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logging.info(event)
    return {
        'statusCode': 200,
        # calling the mid way function and passing all parameters
        'body': Add_Profile(event)
    }

# returns the ProfileId which is needed for all other web service calls – Creates Name, Address, Phone, Email and Data Source Records
# To add a new user to the database
def Add_Profile(event):
    # epsilon endpoint url
    url = "https://webservices-uat-us.unileversolutions.com"

    # Getting the Transaction ID and authenticating the vendor
    Transaction_id = Get_Transaction_ID(
        url + "/Transaction/GetTransactionID/data")

    # calling function to authenticate the vendor
    Authentication = Get_Vendor_Authentication(
        url + "/Oauth2/AuthenticateVendor/Authorize")

    null = None
    
    # json body object parameters needed for add profile call
    Add_Profile_Object = {
        "ClientID": "USTDO",
        "TransactionID": Transaction_id,
        "GlobalOptOut": "",
        "PreferredChannelCode": "",
        "NamePrefix": "",
        "FirstName": f"{''if('FirstName' not in event) else event['FirstName']}",
        "MiddleInit": "",
        "LastName": f"{''if('LastName' not in event) else event['LastName']}",
        "Gender": "",
        "MaritalStatus": "",
        "NameSuffix": "",
        "BirthDate": "",
        "LanguageCode": "",
        "SalutationID": "",
        "SourceCode": "",
        "DataSourceId": f"{''if('DataSourceID' not in event) else event['DataSourceID']}",
        "AccountVerify": "Y",
        "AccountVerifyDate": null,
        "CountryCode": "",
        "UserID": "",
        "ProfilePassword": "",
        "ProfilePasswordSalt": "",
        "EncryptionType": 0,
        "Address": {
            "AddressID": "",
            "AddressLine1": f"{''if('AddressLine1' not in event) else event['AddressLine1']}",
            "AddressLine2": "",
            "City": "",
            "State": "",
            "PostalCode": f"{''if('PostalCode' not in event) else event['PostalCode']}",
            "Country": "",
            "ChannelCode": "DM",
            "Location": "P",
            "DeliveryStatus": "A",
            "Status": "A",
            "IsPreferred": "Y"
        }, "Cookies": {
            "UserId": "",
            "SourceCookie": ""
        }, "Emails": {
            "EmailID": "",
            "EmailAddr": f"{''if('EmailAddr' not in event) else event['EmailAddr']}",
            "ChannelCode": "EM",
            "Location": "P",
            "DeliveryStatus": "A",
            "Status": "A",
            "IsPreferred": "Y"
        }, "Phones": {
            "PhoneID": "",
            "PhoneNumber": "",
            "ChannelCode": "PH",
            "Location": "M",
            "DeliveryStatus": "G",
            "Status": "A",
            "IsPreferred": "Y"
        }, "SocialProfiles": {
            "SocialUID": "",
            "SocialProvider": "",
            "PhotoURL": "",
            "ProfileURL": "",
            "SocialAccessToken": "",
            "Status": "A"
        }, "ExternalInfo": "",
        "CultureInfo": ""
    }
    
    # headers for the post request to add a profile
    headers = {
        'Content-Type': "application/json",
        'Authorization': f"VENDOR {Authentication['AccessToken']}",
        'User-Agent': "PostmanRuntime/7.13.0",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "3cde94d6-5ce4-4a8b-9a64-5b48ca4f2a1c,a781ae0f-0e19-4371-aa78-c8b589a8ad5a",
        'Host': "webservices-uat-us.unileversolutions.com",
        'cookie': "ASP.NET_SessionId=l53klnlcqtwwp34bymn3wvwx",
        'accept-encoding': "gzip, deflate",
        'content-length': "1369",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    response = requests.request(
        "POST", url + "/Profile/AddProfile/data", data=json.dumps(Add_Profile_Object).replace('\\"', ''), headers=headers)

    # converting json gotten from API post request to python dictionary for better processing
    Add_Profile_Object_Result = json.loads(response.text)

    # if add profile fails, return an error to the user for debugging
    if "ErrorDesc" in Add_Profile_Object_Result:
        raise Exception(Add_Profile_Object_Result)

     # callling the function which makes a post to the epsilon database for add promotion responses
    Add_Promotion = Add_Promotion_Responses(url + "/Promotion/AddPromotionResponses/data",
                                            Authentication, Transaction_id, Add_Profile_Object_Result, event)

    # if add promotion responses fails, return an error to the user for debugging
    if "ErrorDesc" in Add_Promotion:
        raise Exception(Add_Promotion)

    # callling the function which makes a post to the epsilon database for add survey profile responses
    Add_Survey = Add_Survey_Profile_Responses(url + "/Survey/AddSurveyProfileResponses/data",
                                              Authentication, Transaction_id, Add_Profile_Object_Result, event)
   

    # if add survey profile responses fails, return an error to the user for debugging
    if "ErrorDesc" in Add_Survey:
        raise Exception(Add_Survey)

    # final result in json
    final_result_json = {
        "TransactionID": Transaction_id,
        "Vendor": Authentication,
        "Add Profile": {
            "Request":  Add_Profile_Object,
            "Response": Add_Profile_Object_Result
        },
        "Add Survey Profile Responses": Add_Survey,
        "Add Promotion Responses": Add_Promotion
    }
    
    logger.info(final_result_json)
    return final_result_json


def Get_Transaction_ID(url):

    # headers for the post request to get Transaction Id
    headers = {
        "User-Agent": "PostmanRuntime/7.13.0",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
        "Postman-Token": "a3c774a2-3f78-4d02-9583-5cd80198b511,a44b9620-8e30-47d6-be7e-9cf9ee5544a2",
        "Host": "webservices-uat-us.unileversolutions.com",
        "cookie": "ASP.NET_SessionId=l53klnlcqtwwp34bymn3wvwx",
        "accept-encoding": "gzip, deflate",
        "content-length": "",
        "Connection": "keep-alive",
        "cache-control": "no-cache"
    }

    # requests going through without headers so removed for now
    response = requests.post(url)

    Transaction_ID = response.text

    logging.info(Transaction_ID)
    # returning Transaction ID as a string
    return Transaction_ID


# Using the client_key and client_secret provided by Epsilon to authenticate the vendor (Ustudio)
def Get_Vendor_Authentication(url):

    # arguments being passed in the url i.e grant type, unique client id and client secret which should not be shared
    querystring = {"Grant_type": "vendor", "Client_id": "USTDO",
                   "Client_secret": "qyjn78VTbmUW3hpk5dGApH6d"}

    payload = ""

    # headers for the post request to get Authentication Object
    headers = {
        'Authorization': "qyjn78VTbmUW3hpk5dGApH6d",
        'Content-Type': "application/x-www-form-urlencoded",
        'User-Agent': "PostmanRuntime/7.13.0",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "046708f2-2dca-442c-ba4f-cc0ccade52b3,6f6f800f-d42f-48f5-b238-1b2a109827fe",
        'Host': "webservices-uat-us.unileversolutions.com",
        'cookie': "ASP.NET_SessionId=l53klnlcqtwwp34bymn3wvwx",
        'accept-encoding': "gzip, deflate",
        'content-length': "",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    # requests going through without headers so removed for now
    response = requests.request("POST", url, data=payload, params=querystring)

    # converting json to python dictionary
    Authentication_Object = json.loads(response.text)

    logging.info(Authentication_Object)
    # returning Authentication Object
    return Authentication_Object


# Function to add promotion responses gotten from the user.

def Add_Promotion_Responses(url, Authentication, Transaction_id, Add_Profile, event):

    # headers for the add promotion responses
    headers = {
        'Authorization': f"VENDOR {Authentication['AccessToken']}",
        'Content-Type': "application/json",
        'User-Agent': "PostmanRuntime/7.13.0",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "9658036c-7ef6-4911-9aa8-d0aa5502c0fe,9ac2beec-cc59-4239-8112-ebbe41276f26",
        'Host': "webservices-uat-us.unileversolutions.com",
        'cookie': "ASP.NET_SessionId=l53klnlcqtwwp34bymn3wvwx",
        'accept-encoding': "gzip, deflate",
        'content-length': "460",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

  
    Add_Promotion_Responses_Object = {
        "ClientID": "USTDO",
        "TransactionID": Transaction_id,
        "ProfileID": Add_Profile['NewProfileID'],
        "EmailAddress": f"{''if('EmailAddr' not in event) else event['EmailAddr']}",
        "PromotionResponses": add_promotion_ccids_to_json(event),
        "ExternalInfo": "",
        "CultureInfo": ""

    }
    
    response = requests.request("POST", url, data=json.dumps(
        Add_Promotion_Responses_Object).replace('\\"', '').replace('\\\\', '\\'), headers=headers)
        
    Add_Promotion_Responses_Object_Result = json.loads(response.text)
    
    tmp_add_promotion_responses = {
        "Request":  Add_Promotion_Responses_Object,
        "Response": Add_Promotion_Responses_Object_Result
    }
    
    logging.info(tmp_add_promotion_responses)
    # returning Add Promotion Request and Response
    return tmp_add_promotion_responses

# SurveyProfileResponses is typically used for Survey Question Answer Pairs and Subscriptions. 
# Epsilon will provide vendors with the SQAID (SurveyQuestionAnswerId) needed for each implementation. For Subscriptions, 2 SQAIDs will be provided – one for Opt Ind and one for Opt Out.
def Add_Survey_Profile_Responses(url, Authentication, Transaction_id, Add_Profile, event):

    # headers for the post request to add a survey profile response
    headers = {
        'Authorization': f"VENDOR {Authentication['AccessToken']}",
        'Content-Type': "application/json",
        'User-Agent': "PostmanRuntime/7.13.0",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        'Postman-Token': "2f085b3f-b457-4c8b-a27b-fe5bc0a80184,845ae86b-4da9-412d-968c-a41c829078b9",
        'Host': "webservices-uat-us.unileversolutions.com",
        'cookie': "ASP.NET_SessionId=l53klnlcqtwwp34bymn3wvwx",
        'accept-encoding': "gzip, deflate",
        'content-length': "446",
        'Connection': "keep-alive",
        'cache-control': "no-cache"
    }

    # json body object parameters needed for add survey profile responses call
    Add_Survey_Profile_Responses_Object = {
        "ClientID": "USTDO",
        "TransactionID": Transaction_id,
        "ProfileID": Add_Profile['NewProfileID'],
        "ProgramCode": "",
        "DataSourceId":  f"{''if('DataSourceID' not in event) else event['DataSourceID']}",
        "SurveyProfileResponses": survey_profile_responses_to_json(event),
        "ExternalInfo": "",
        "CultureInfo": ""
    }

   
    response = requests.request("POST", url, data=json.dumps(
        Add_Survey_Profile_Responses_Object).replace('\\"', ''), headers=headers)
   
    
    # converting json to python dictionary
    Add_Survey_Profile_Responses_Object_Result = json.loads(response.text)

    tmp_add_survey_profile_responses = {
        "Request":  Add_Survey_Profile_Responses_Object,
        "Response": Add_Survey_Profile_Responses_Object_Result
    }
    
    logging.info(tmp_add_survey_profile_responses)
    # return Add Survey profile responses Request and Response.
    return tmp_add_survey_profile_responses


# function to convert to json milliseconds
def time_converter(val):
    
    # logging the current time of each call for debugging.
    logging.info(datetime.now())
    
    # if time data was collected is given, convert that time to json milliseconds
    if len(val) > 2:
        return int(datetime.strptime(val, '%Y-%m-%d %H:%M').strftime("%s")) * 1000
    else:
        # if time wasnt given then convert current time to json milliseconds
        return int(datetime.now().strftime("%s")) * 1000
    

# function to get all survey questions and put into a json array
def survey_profile_responses_to_json(event):
    
    # empty list to loop through data given and add all survey questions
    questions_list = []
    
    # with old wyng campaign format, we would get a key called "Fields" containing all the data gotten from the user
    try:
        # works for getting questions list from wyng, converting the dict to json
        tmp_old_values = json.dumps(event['Fields'])
        conv_tmp_old_values_json = json.loads(
            tmp_old_values.replace("\'", "\""))
    except ValueError:
        # works for getting questions list from postman, since data is already in json
        # currently used for testing
        tmp_old_values = event['Fields']
        conv_tmp_old_values_json = json.loads(
            tmp_old_values.replace("\'", "\""))
    finally:
        final_conversion = conv_tmp_old_values_json['quiz_choices']

    # getting the first question and putting it into the question list
    if(final_conversion[0] == "405086"):
        tmp = {}

        tmp["AnswerID"] = "2000078000"
        tmp["SurveyQuestionAnswerID"] = "2000149000"
        tmp["SurveyTextResponse"] = "Fine"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[0] == "405087"):
        tmp = {}

        tmp["AnswerID"] = "2000078001"
        tmp["SurveyQuestionAnswerID"] = "2000149001"
        tmp["SurveyTextResponse"] = "Medium"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[0] == "405088"):
        tmp = {}

        tmp["AnswerID"] = "2000078002"
        tmp["SurveyQuestionAnswerID"] = "2000149002"
        tmp["SurveyTextResponse"] = "Thick"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

        # getting the second question and putting it into the question list
    if(final_conversion[1] == "405089"):
        tmp = {}

        tmp["AnswerID"] = "2000078003"
        tmp["SurveyQuestionAnswerID"] = "2000149003"
        tmp["SurveyTextResponse"] = "Dry hair"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[1] == "405090"):
        tmp = {}

        tmp["AnswerID"] = "2000078004"
        tmp["SurveyQuestionAnswerID"] = "2000149004"
        tmp["SurveyTextResponse"] = "Damaged hair"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[1] == "405091"):
        tmp = {}

        tmp["AnswerID"] = "2000078005"
        tmp["SurveyQuestionAnswerID"] = "2000149005"
        tmp["SurveyTextResponse"] = "Flat, limp hair"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

        # getting the third question and putting it into the question list
    if(final_conversion[2] == "405092"):
        tmp = {}

        tmp["AnswerID"] = "2000078006"
        tmp["SurveyQuestionAnswerID"] = "2000149006"
        tmp["SurveyTextResponse"] = "I mainly use Dove"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[2] == "405093"):
        tmp = {}

        tmp["AnswerID"] = "2000078007"
        tmp["SurveyQuestionAnswerID"] = "2000149007"
        tmp["SurveyTextResponse"] = "I mainly use another brand"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[2] == "405094"):
        tmp = {}

        tmp["AnswerID"] = "2000078008"
        tmp["SurveyQuestionAnswerID"] = "2000149008"
        tmp["SurveyTextResponse"] = "I try different brands"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)

    elif(final_conversion[2] == "405095"):
        tmp = {}

        tmp["AnswerID"] = "2000078009"
        tmp["SurveyQuestionAnswerID"] = "2000149009"
        tmp["SurveyTextResponse"] = "I don't use conditioner"
        tmp["DeleteResponseFlag"] = "N"

        questions_list.append(tmp)
    
    logging.info(questions_list)
    return questions_list

# function to get all CCID's and put into a json array
def add_promotion_ccids_to_json(event):
    
    # calling the function to get the date and time given converted to json milliseconds
    # if the time was given if not send an empty field to the function and get the current time back
    current_time = time_converter(
        event['Time(UTC)']) if 'Time(UTC)' in event else time_converter("")
        
    # getting list of CCID's gotten from the client
    ccids = event['CampaignControlID']
    
    # final list of ccids
    ccids_list = []
    
    # looping through all campaign control ids gotten from the client
    for ccid in ccids:
        tmp = {
                "RecordDate": f"\/Date({current_time})\/",
                "CampaignControlID": ccid,
                "MediaOriginCode": "",
                "UserAgentString": "",
                "Device": "",
                "Platform": "",
                "Latitude": "",
                "Longitude": "",
                "SKU": "",
                "DataSourceID": f"{''if('DataSourceID' not in event) else event['DataSourceID']}"
            }
            
        ccids_list.append(tmp)    
 
    # if optin is gotten from client, add both optin ccids
    if("OptIn" in event and event["OptIn"] is not None): 
        
        tmp_optin_brand = {
                "RecordDate": f"\/Date({current_time})\/",
                "CampaignControlID": "9000183481",
                "MediaOriginCode": "",
                "UserAgentString": "",
                "Device": "",
                "Platform": "",
                "Latitude": "",
                "Longitude": "",
                "SKU": "",
                "DataSourceID": f"{''if('DataSourceID' not in event) else event['DataSourceID']}"
            }
        ccids_list.append(tmp_optin_brand) 
        
        tmp_optin_unilever_corporate = {
                "RecordDate": f"\/Date({current_time})\/",
                "CampaignControlID": "9000001779",
                "MediaOriginCode": "",
                "UserAgentString": "",
                "Device": "",
                "Platform": "",
                "Latitude": "",
                "Longitude": "",
                "SKU": "",
                "DataSourceID": f"{''if('DataSourceID' not in event) else event['DataSourceID']}"
            }
        ccids_list.append(tmp_optin_unilever_corporate) 
     
    logging.info(ccids_list)
    return ccids_list
        
        
    
