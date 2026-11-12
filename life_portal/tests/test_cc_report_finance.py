import importlib.util, sys, types, unittest
class Row(dict):
    def __getattr__(self,key): return self.get(key)
class Tests(unittest.TestCase):
    def test_scoped_active_mapping_and_unmapped_retention(self):
        queries=[]
        employees=[Row(name='E1',employee_name='Consultant',designation='Doctor',branch='A'),Row(name='M1',employee_name='Center Manager',designation='Center Manager',branch='A'),Row(name='M2',employee_name='Senior Manager',designation='Senior Manager',branch='A')]
        def get_all(dt,**kw):
            queries.append((dt,kw))
            if dt=='Patient':return [Row(name='P1',custom_lead='L1',custom_employee_id='E1'),Row(name='P2',custom_lead='L2',custom_employee_id='LEFT')]
            if dt in ('Therapy Plan','Healthcare Practitioner'):return []
            if dt=='Employee':return [r for r in employees if ('name' not in kw['filters'] or r.name in kw['filters']['name'][1])]
            raise AssertionError(dt)
        fake=types.SimpleNamespace(db=types.SimpleNamespace(exists=lambda *a:True),get_meta=lambda dt:types.SimpleNamespace(has_field=lambda field:True),get_all=get_all,get_list=get_all,PermissionError=PermissionError)
        original=sys.modules.get('frappe');sys.modules['frappe']=fake
        try:
            spec=importlib.util.spec_from_file_location('report_finance','life_slimming/api/cc_report_finance.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
            result=mod.enrich_appointment_consultants([{'name':'L1','branch':'A','custom_appointment_date_and_time':'2026-11-12'},{'name':'L2','branch':'A','custom_appointment_date_and_time':'2026-11-12'}],[])
            self.assertEqual(result[0]['consultant_name'],'Consultant');self.assertEqual(result[0]['manager_name'],'Senior Manager');self.assertFalse(result[1]['consultant_eligible']);self.assertEqual(len(result),2)
            self.assertEqual(queries[0][1]['filters']['custom_lead'][1],['L1','L2'])
        finally:
            if original is None:sys.modules.pop('frappe',None)
            else:sys.modules['frappe']=original
if __name__ == '__main__':
    unittest.main()
