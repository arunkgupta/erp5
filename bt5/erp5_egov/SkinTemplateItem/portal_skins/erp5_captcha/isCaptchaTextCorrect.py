request = context.REQUEST
session_id = request.get('erp5_captcha_session_id', None)
if session_id is None:
  return 'no session'
# get session
session = context.portal_sessions[session_id]

if session.has_key('captcha_text') and  session.has_key('captcha_image_path'):
  captcha_text = session['captcha_text']
  captcha_file_path = session['captcha_image_path']

if text_to_check == captcha_text:
  return True

return False
