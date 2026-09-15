set heading off feedback off pagesize 0 verify off echo off
whenever sqlerror exit failure
select 'THEME_FACTORY_TARGET=' || json_object(
           'appId' value a.application_id,
           'alias' value a.alias,
           'name' value a.application_name,
           'workspace' value a.workspace,
           'apexVersion' value r.version_no
         returning varchar2)
  from apex_applications a
 cross join apex_release r
 where a.application_id = to_number('&1')
   and upper(a.workspace) = upper('&2');
exit
