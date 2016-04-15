# Jump to the items related to current amortisation transaction

search_list = context.getCausalityValueList(
     portal_type = context.getPortalItemTypeList()
)
selection_uid_list = [x.getUid() for x in search_list]

request=context.REQUEST
if len(selection_uid_list) != 0 : 
  kw = {'uid': selection_uid_list}
  context.portal_selections.setSelectionParamsFor('Base_jumpToRelatedObjectList', kw)
  request.set('uids', selection_uid_list)
  return context.Base_jumpToRelatedObjectList(
        uids=selection_uid_list, REQUEST=request)

redirect_url = '%s/view?%s' % (context.getPath(),
            'portal_status_message=No+Related+Item+For+Current+Amortisation+Transaction')
return context.REQUEST[ 'RESPONSE' ].redirect(redirect_url)
