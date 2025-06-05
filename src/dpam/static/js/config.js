//SSO server for production
//ch200409:layer4 load balancer
var ssoLoginUrl = "http://inlcnws.cminl.oa/InxSSOv3/Logon.aspx";
var verifyUrl = "http://inlcnws.cminl.oa/InxSSOv3/VerifyTicket.ashx";
//var ssoLoginUrl = "http://jnb2bws01.cminl.oa/InxSSOv3/Logon.aspx";
//var verifyUrl = "http://jnb2bws01.cminl.oa/InxSSOv3/VerifyTicket.ashx";

//SSO server for testing
//var ssoLoginUrl = "http://jnvtpwstest.cminl.oa/InxSSOv3/Logon.aspx";
//var verifyUrl = "http://jnvtpwstest.cminl.oa/InxSSOv3/VerifyTicket.ashx";

var aListUrl = "http://tnvwsap01.cminl.oa/Authority/api/AVO/GetFunctionAuth";
var vLogUrl = "http://tnvwsap01.cminl.oa/Authority/api/AVO/CheckFuncAuth";

//var defaultFuncId = "65DBD839798E2046E053C582380A1796"; // DAP 2.1 EDC L6
var defaultFuncId = "788F374A2663557AE053C582380A6BF1"; // QM4.0 1.3.2.KFM
                     
var validFuncIdList = [
  "631CE456B7CA43E2E053C582380AB35D", // I-Dictionary 5.5.DOE
  "65DBD839798E2046E053C582380A1796", // DAP 2.1 EDC L6
];

//ch190124:readable app identifier
var appId = "api_account";

//ch190226:only authenticate user, skip validating user
var isSkipValidation = true;