Subject: LIFE Portal ConVox integration — final configuration and joint testing

Hi Team,

We have implemented click-to-call in LIFE Portal and automatic token retrieval
through `/ConVoxCCS/rest/secureToken`. Token retrieval from our local backend is
successful. As confirmed, we use the returned `REFRESH_TOKEN` as the `Access-Token`
header for click-to-call. All 14 supplied agent IDs and emails are mapped locally.

AES-256-CBC widget encryption is implemented and tested, and the confirmed secret
and IV are configured. Live encrypted sign-in and actual calling are pending.

Please confirm:

1. The dial prefix for our deployment. Your document shows `11` as an example;
   please confirm the actual value and whether it differs by agent/process.
2. Whether the SSO IV must be Base64-decoded to 16 bytes or passed literally as
   in the PHP example (using its first 16 bytes). Please also confirm that the
   supplied emails are mapped for `ExternalUserName` on your server.
3. Click-to-call, Call Popup and Call Status APIs are enabled for our processes.
4. The widget supports embedding with microphone access from our LIFE Portal
   origin, including the required telephony connectivity.

We have implemented popup/status callback endpoints with `X-ConVox-Token`
authentication. Once our public HTTPS callback base URL is finalized, please
configure both callback URLs and the agreed header on your side. Our current
localhost address is not reachable by your server.

Please arrange a joint test with a designated agent and test phone number for
encrypted sign-in, outbound/inbound calls, audio, and callback delivery.

Thank you,
Narendhar
