SET @current_path = NULL; <dtml-var sql_delimiter>
SET @current_reference = NULL; <dtml-var sql_delimiter>

<dtml-let query="portal_catalog.buildSQLQuery(query=portal_catalog.getSecurityQuery(), portal_type=getPortalDocumentTypeList())">
<dtml-let user_language="Localizer.get_selected_language()">
SELECT path, uid
FROM
(
SELECT DISTINCT
sub.path,
uid
FROM
( SELECT
    @current_path:=IF(@current_reference = reference, @current_path, path) AS path,
    @current_reference:=reference AS reference
  FROM (
    SELECT DISTINCT
      reference,
      path,
      catalog.uid,
      CASE language WHEN <dtml-sqlvar user_language type=string> THEN 1 WHEN 'en' THEN 0 ELSE -1 END as language_order
    FROM
      catalog, versioning
    WHERE
      catalog.uid = versioning.uid
      <dtml-if "query['where_expression']">
      AND <dtml-var "query['where_expression']">
      </dtml-if>
      AND
        (
         <dtml-in reference_list>
           <dtml-sqltest "_['sequence-item']" column=reference op=eq type=string>
           <dtml-unless sequence-end> OR </dtml-unless>
         </dtml-in>
        )
    ORDER BY reference, language_order DESC, version DESC, revision DESC
  ) AS innersub
)
AS sub inner join catalog on catalog.path = sub.path
)
AS main
WHERE
<dtml-sqltest "getUid()" column=uid op=ne type=int>
LIMIT 1000

</dtml-let>
</dtml-let>
