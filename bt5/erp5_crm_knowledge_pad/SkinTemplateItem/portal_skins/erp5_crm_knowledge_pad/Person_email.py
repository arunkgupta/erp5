"""
  Create a CRM "Mail Message" to communication between context person and currrent logged in user.
"""
portal = context.getPortalObject()

new_event = portal.event_module.newContent(portal_type = "Mail Message")
new_event.setDestinationValue(context)
new_event.setSourceValue(portal.ERP5Site_getAuthenticatedMemberPersonValue())

return new_event.Base_redirect("view")
