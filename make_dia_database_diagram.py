#!/usr/bin/python

"""
Converts an SQL schema into a DIA file. It reads SQL CREATE statements from
standard input and writes to standard output. Tested with MySQL. Should be able
to work with other DBMS without much change.

Example:
./make_dia_class_diagram.py < schema.sql > database_diagram.dia
"""

import re
import sys

file_template = '''<?xml version="1.0" encoding="UTF-8"?>
<dia:diagram xmlns:dia="http://www.lysator.liu.se/~alla/dia/">
  <dia:layer name="Background" visible="true" active="true">
%(tables)s
  </dia:layer>
</dia:diagram>'''

table_template = '''    <dia:object type="Database - Table" version="0" id="O0">
      <dia:attribute name="name">
        <dia:string>%(name)s</dia:string>
      </dia:attribute>
      <dia:attribute name="attributes">
%(attributes)s
      </dia:attribute>
    </dia:object>'''

attribute_template = '''        <dia:composite type="table_attribute">
          <dia:attribute name="name">
            <dia:string>%(name)s</dia:string>
          </dia:attribute>
          <dia:attribute name="type">
            <dia:string>%(type)s</dia:string>
          </dia:attribute>
          <dia:attribute name="primary_key">
            <dia:boolean val="%(is_primary)s"/>
          </dia:attribute>
          <dia:attribute name="nullable">
            <dia:boolean val="%(is_nullable)s"/>
          </dia:attribute>
        </dia:composite>'''

re_flags = re.IGNORECASE|re.DOTALL

def make_table(name, attributes):
  """Makes and returns a table object."""
  return {'name':name,'attributes':attributes}

def make_attribute(name, type, is_primary, is_nullable):
  """Makes and returns an attribute object."""
  return {
    'name':name,
    'type':type,
    'is_primary':is_primary,
    'is_nullable':is_nullable,
  }


def get_primary_keys_and_plain_attributes_mysql(attribs_text):
  """
  Takes attributes defined inside a CREATE TABLE statement and returns the
  primary keys and the attributes splitted into name and params.
  """
  
  attribute_def_re = re.compile(
    r'(?P<name>\w+)\W+(?P<params>[^(,]+([(][^)]*[^,]+)?),',re_flags)
  primary_keys_re = re.compile(r'[(](?P<primary_keys>[^)]*)[)]',re_flags)
  primary_key_re = re.compile(r'(\w+)',re_flags)
  
  last_paren = attribs_text.rfind(')')
  attribs_text = attribs_text[:last_paren-1]+','+attribs_text[last_paren:]
  primary_keys = []
  attributes = []
  for attribute_match in attribute_def_re.finditer(attribs_text):
    name = attribute_match.group('name')
    params = attribute_match.group('params')
    if name.lower() == 'primary':
      primary_keys_text = primary_keys_re.search(params).group('primary_keys')
      primary_keys = primary_key_re.findall(primary_keys_text)
    elif name.lower() == 'key':
      pass
    else:
      attributes.append({'name':name,'params':params})
  return (primary_keys,attributes)

def get_attribute_mysql(attribute, primary_keys):
  """Transforms an attribute from SQL format to internal attribute format."""
  
  not_null_re = re.compile(r'NOT\W+NULL',re_flags)
  type_re = re.compile(r'(?P<type>\w+([(][^)]*[)])?)',re_flags)

  is_primary = attribute['name'] in primary_keys
  is_nullable = not_null_re.search(attribute['params']) == None
  type = type_re.search(attribute['params']).group('type')
  return make_attribute(attribute['name'], type, is_primary, is_nullable)

def read_attributes_mysql(table_match):
  """
  Takes a CREATE TABLE statement and reads attributes defined inside. Returns an
  array of attributes.
  """
  
  attribs_text = table_match.group('attributes_text')
  ret = get_primary_keys_and_plain_attributes_mysql(attribs_text)
  (primary_keys,plain_attributes) = ret
  
  attributes = []
  for attribute in plain_attributes:
    attrib = get_attribute_mysql(attribute, primary_keys)
    attributes.append(attrib)
  return attributes
  
def read_tables_mysql(text):
  """
  Reads an SQL schema, splits CREATE TABLE statements and processes each one
  of them. Returns an array of tables.
  """
  
  create_table_stmt_re = re.compile(
    r'CREATE\W+TABLE\W+(?P<name>\w+)(?P<attributes_text>[^;]*);',re_flags)
  
  tables = []
  for table_match in create_table_stmt_re.finditer(text):
    attributes = read_attributes_mysql(table_match)
    table = make_table(table_match.group('name'), attributes)
    tables.append(table)
  return tables

def read_input_mysql(text):
  """
  Reads an SQL schema for MySQL from standard input. Returns an array of
  tables.
  """
  return read_tables_mysql(text)
    
def write_output(tables):
  """Writes a DIA file to the output."""
  tables_text = ''
  for table in tables:
    attributes_text = ''
    for attribute in table['attributes']:
      params = {
        'name':'#'+attribute['name']+'#',
        'type':'#'+attribute['type']+'#',
        'is_primary':str(attribute['is_primary']).lower(),
        'is_nullable':str(attribute['is_nullable']).lower(),
      }
      attributes_text += attribute_template % params
    params = {
      'name':'#'+table['name']+'#',
      'attributes':attributes_text,
    }
    tables_text += table_template % params
  print file_template % {'tables':tables_text}

def main():
  write_output(read_input_mysql(sys.stdin.read()))

if __name__ == '__main__':
  main()
