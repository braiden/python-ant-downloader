# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import logging
import os
import sys
import requests
import json
import glob
import time
import re
import tempfile

import antd.plugin as plugin

_log = logging.getLogger("antd.connect")

class GarminConnect(plugin.Plugin):

    username = None
    password = None

    logged_in = False
    login_invalid = False
    
    rsession = None

    def __init__(self):
        rate_lock_path = tempfile.gettempdir() + "/gc_rate.%s.lock" % "0.0.0.0"
        # Ensure the rate lock file exists (...the easy way)
        open(rate_lock_path, "a").close()
        self._rate_lock = open(rate_lock_path, "r+")
        return
    
    # Borrowed to support new Garmin login
    # https://github.com/cpfair/tapiriik
    def _rate_limit(self):
        import fcntl, struct, time
        print("Waiting for lock")
        min_period = 1  # I appear to been banned from Garmin Connect while determining this.
        fcntl.flock(self._rate_lock,fcntl.LOCK_EX)
        try:
            self._rate_lock.seek(0)
            last_req_start = self._rate_lock.read()
            if not last_req_start:
                last_req_start = 0
            else:
                last_req_start = float(last_req_start)

            wait_time = max(0, min_period - (time.time() - last_req_start))
            time.sleep(wait_time)

            self._rate_lock.seek(0)
            self._rate_lock.write(str(time.time()))
            self._rate_lock.flush()
        finally:
            fcntl.flock(self._rate_lock,fcntl.LOCK_UN)

    # work around old versions of requests
    def get_response_text(self, response):
        return response.text if hasattr(response, "text") else response.content
    
    def data_available(self, device_sn, format, files):
        if format not in ("tcx"): return files
        result = []
        try:
            for file in files:
                self.login()
                self.upload(format, file)
                result.append(file)
            plugin.publish_data(device_sn, "notif_connect", files)
        except Exception:
            _log.warning("Failed to upload to Garmin Connect.", exc_info=True)
        finally:
            return result

    def login(self):
        if self.logged_in: return
        if self.login_invalid: raise InvalidLogin()
        
        # Use a session, removes the need to manage cookies ourselves
        self.rsession = requests.Session()
        
        _log.debug("Checking to see what style of login to use for Garmin Connect.")
        #Login code taken almost directly from https://github.com/cpfair/tapiriik/
        self._rate_limit()
        gcPreResp = self.rsession.get("http://connect.garmin.com/", allow_redirects=False)
        # New site gets this redirect, old one does not
        if gcPreResp.status_code == 200:
            _log.debug("Using old login style")
            params = {"login": "login", "login:loginUsernameField": self.username, "login:password": self.password, "login:signInButton": "Sign In", "javax.faces.ViewState": "j_id1"}
            auth_retries = 3 # Did I mention Garmin Connect is silly?
            for retries in range(auth_retries):
                self._rate_limit()
                resp = self.rsession.post("https://connect.garmin.com/signin", data=params, allow_redirects=False, cookies=gcPreResp.cookies)
                if resp.status_code >= 500 and resp.status_code < 600:
                    raise APIException("Remote API failure")
                if resp.status_code != 302:  # yep
                    if "errorMessage" in self.get_response_text(resp):
                        if retries < auth_retries - 1:
                            time.sleep(1)
                            continue
                        else:
                            login_invalid = True
                            raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
                    else:
                        raise APIException("Mystery login error %s" % self.get_response_text(resp))
                _log.debug("Old style login complete")
                break
        elif gcPreResp.status_code == 302:
            _log.debug("Using new style login")
            # JSIG CAS, cool I guess.
            # Not quite OAuth though, so I'll continue to collect raw credentials.
            # Commented stuff left in case this ever breaks because of missing parameters...
            data = {
                "username": self.username,
                "password": self.password,
                "_eventId": "submit",
                "embed": "true",
                # "displayNameRequired": "false"
            }
            params = {
                "service": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
                # "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
                # "webhost": "olaxpw-connect00.garmin.com",
                "clientId": "GarminConnect",
                # "gauthHost": "https://sso.garmin.com/sso",
                # "rememberMeShown": "true",
                # "rememberMeChecked": "false",
                "consumeServiceTicket": "false",
                # "id": "gauth-widget",
                # "embedWidget": "false",
                # "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
                # "source": "http://connect.garmin.com/en-US/signin",
                # "createAccountShown": "true",
                # "openCreateAccount": "false",
                # "usernameShown": "true",
                # "displayNameShown": "false",
                # "initialFocus": "true",
                # "locale": "en"
            }
            _log.debug("Fetching login variables")
            
            # I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
            preResp = self.rsession.get("https://sso.garmin.com/sso/login", params=params)
            if preResp.status_code != 200:
                raise APIException("SSO prestart error %s %s" % (preResp.status_code, self.get_response_text(preResp)))
            data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", self.get_response_text(preResp)).groups(1)[0]
            _log.debug("lt=%s"%data["lt"])

            _log.debug("Posting login credentials to Garmin Connect. username=%s", self.username)
            ssoResp = self.rsession.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
            if ssoResp.status_code != 200:
                login_invalid = True
                _log.error("Login failed")
                raise APIException("SSO error %s %s" % (ssoResp.status_code, self.get_response_text(ssoResp)))

            ticket_match = re.search("ticket=([^']+)'", self.get_response_text(ssoResp))
            if not ticket_match:
                login_invalid = True
                raise APIException("Invalid login", block=True, user_exception=UserException(UserExceptionType.Authorization, intervention_required=True))
            ticket = ticket_match.groups(1)[0]

            # ...AND WE'RE NOT DONE YET!

            self._rate_limit()
            gcRedeemResp = self.rsession.get("https://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
            if gcRedeemResp.status_code != 302:
                raise APIException("GC redeem-start error %s %s" % (gcRedeemResp.status_code, gcRedeemResp.text))

            # There are 6 redirects that need to be followed to get the correct cookie
            # ... :(
            expected_redirect_count = 6
            current_redirect_count = 1
            while True:
                self._rate_limit()
                gcRedeemResp = self.rsession.get(gcRedeemResp.headers["location"], allow_redirects=False)

                if current_redirect_count >= expected_redirect_count and gcRedeemResp.status_code != 200:
                    raise APIException("GC redeem %d/%d error %s %s" % (current_redirect_count, expected_redirect_count, gcRedeemResp.status_code, gcRedeemResp.text))
                if gcRedeemResp.status_code == 200 or gcRedeemResp.status_code == 404:
                    break
                current_redirect_count += 1
                if current_redirect_count > expected_redirect_count:
                    break

        else:
            raise APIException("Unknown GC prestart response %s %s" % (gcPreResp.status_code, self.get_response_text(gcPreResp)))

        
        self.logged_in = True
        
    
    def upload(self, format, file_name):
        #TODO: Restore streaming for upload
        with open(file_name) as file:
            files = {'file': file}
            _log.info("Uploading %s to Garmin Connect.", file_name)
            r = self.rsession.post("https://connect.garmin.com/proxy/upload-service-1.1/json/upload/.%s" % format, files=files)
        
class StravaConnect(plugin.Plugin):

    server = None
    smtp_server = None
    smtp_port = None
    smtp_username = None
    smtp_password = None

    logged_in = False

    def __init__(self):
        from smtplib import SMTP
        self.server = SMTP()
        pass

    def data_available(self, device_sn, format, files):
        if format not in ("tcx"): return files
        result = []
        try:
            for file in files:
                self.login()
                self.upload(format, file)
                result.append(file)
            self.logout()
        except Exception:
            _log.warning("Failed to upload to Strava.", exc_info=True)
        finally:
            return result

    def logout(self):
        self.server.close()

    def login(self):
        if self.logged_in: return
        self.server.connect(self.smtp_server, self.smtp_port)
        self.server.ehlo()
        self.server.starttls()
        self.server.ehlo()
        self.server.login(self.smtp_username, self.smtp_password)
        self.logged_in = True
    
    def upload(self, format, file_name):
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        import datetime
        from email import encoders
        outer = MIMEMultipart()
        outer['Subject'] = 'Garmin Data Upload from %s' % datetime.date.today()
        outer['To' ] = 'upload@strava.com'
        outer['From' ] = self.smtp_username
        outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
        with open(file_name, 'rb') as fp:
            msg = MIMEBase('application', 'octet-stream')
            msg.set_payload(fp.read())
        encoders.encode_base64(msg)
        msg.add_header('Content-Disposition', 'attachment', filename=file_name)
        outer.attach(msg)
        self.server.sendmail(self.smtp_username, 'upload@strava.com', outer.as_string())

class InvalidLogin(Exception): pass


# vim: ts=4 sts=4 et
