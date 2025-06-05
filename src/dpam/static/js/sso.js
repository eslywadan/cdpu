if (!document.all) {
  var key = getParameterByName("CertificateKey");
  if (key) {
    var userId = verifyTicket(verifyUrl, key);
    if (userId !=="") {
      if (userId == "_error_") {
        var keyParam = "CertificateKey=" + encodeURIComponent(key);
        var reg = new RegExp(keyParam,"i");
        var oldUrl = location.href.replace(reg, "re=.").replace(".&re=.", "..");
        location.href = ssoLoginUrl + "?url=" + encodeURIComponent(oldUrl);
      }
      else if (isSkipValidation) {
        if (typeof onCheckedUserOK !== 'undefined' && onCheckedUserOK) {
          onCheckedUserOK(userId);
        }

        //ch190124:write session cookie for Docker EE
        writeSessionCookie(key);
      }
      else {
        var funcId = getFuncId();
        var authInfo = checkAuthorization(aListUrl, funcId, userId);
        if (authInfo.AUTH_YN !== true) {
          if (typeof onCheckedUserNG !== 'undefined' && onCheckedUserNG) {
            onCheckedUserNG(userId);
          }
          else {
            alert("You are not allowed to access this app");
            window.location.href="about:blank";
          }
        }
        else {
          checkAuthWithLog(vLogUrl, funcId, userId);
          if (typeof onCheckedUserOK !== 'undefined' && onCheckedUserOK) {
            onCheckedUserOK(userId, authInfo);
          }

          //ch190124:write session cookie for Docker EE
          writeSessionCookie(key);
        }
      }
    }
  }
  else {
    //if (confirm("Go to login page?"))
    location.href = ssoLoginUrl + "?url=" + encodeURIComponent(location.href);
  }
}

function verifyTicket(verifyUrl, key) {
  var userId = "";
  $.ajax({
    url: verifyUrl + "?ticket=" + encodeURIComponent(key),
    dataType: "json",
    async: false,
    success: function(jsTicket) {
     if (jsTicket.ErrorCode) {
        userId = "_error_";
        if (location.href.indexOf("re=..........")>=0)
          alert(jsTicket.ErrorCode + "-" + jsTicket.ErrorMsg + 
            "\r\nOr just refresh/retry too many times. Please click OK to continue.");
     }
     else
       userId = jsTicket.UserId + "|" + jsTicket.EmpId;
    },
    error: function(data) {
      alert(data);
      userId = "_error_";
    }
  });
  
  return userId;
}

function getFuncId() {
  var funcId = getParameterByName("FUNCID");
  if (funcId && validFuncIdList.indexOf(funcId) > -1)
    return funcId;
    
  return defaultFuncId;
}

function checkAuthorization(aListUrl, funcId, userId) {
  var authInfo = {AUTH_YN : false};
  $.ajax({
    url: aListUrl + "?FUNCID=" + funcId + "&UserAD=" + userId,
    dataType: "json",
    async: false,
    success: function(jsnAList) {
      authInfo = jsnAList;
    },
    error: function(data) {
      alert(data);
    }
  });
  
  return authInfo;
}
 
function checkAuthWithLog(vLogUrl, funcId, userId) {
  var isAuthorized = false;
  var jsnData = '{"FuncID":"' + funcId + '", "AdAccount":"' + userId + '"}';
  $.post(vLogUrl, 
    {FuncID: funcId, AdAccount: userId}, 
    function(jsnResult) {
      if (!jsnResult.IsPass)
        alert(jsnResult.Message);
    }, 
    "json"
  );
  
  return isAuthorized;
}
 
function getParameterByName(name) {
  return decodeURIComponent((new RegExp("[?|&]" + name + "=" + "([^&;]+?)(&|#|;|$)").exec(location.search)||[,""])[1].replace(/\\+/g, "%20"))||null;
}
                     
//ch190124:identify app and each user login for Docker EE
function writeSessionCookie(key) {
  //ch200528:skip write session cookie
  if (appId=="") return;

  var name = "session_" + appId;
  var value = key.slice(-25, -5);
  document.cookie = name + "=" + value;
}
