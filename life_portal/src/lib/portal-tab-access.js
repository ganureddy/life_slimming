// Parent module access is evaluated by the caller. Missing tab rules inherit
// access, keeping existing saved role configurations backward compatible.
export function tabAllowed(catalog,config,module,tab) {
 const entries=catalog?.[module]||[],entry=entries.find(value=>value.id===tab);
 if(!entry)return false;
 const rules=config?.tab_access?.[module];
 return rules?.[tab]!==false&&(!entry.parent||tabAllowed(catalog,config,module,entry.parent));
}
