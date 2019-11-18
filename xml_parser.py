import lxml.etree as etree
from xml.etree.ElementTree import tostring


def dynamic_instanciation(tag, child, parent, scope):
    # print 'tag : %s' % tag
    return getattr(__import__(scope), tag)(child, parent)


class SimpleField(object):
    def __init__(self, data, type='string'):
        self.field_name = ''
        self.field_value = data
        self.type = type


class Field(SimpleField):
    def __init__(self, et, type):
        super(Field, self).__init__('', '')
        self.field_name = et.tag
        self.field_value = et.text
        self.type = type

    def __repr_(self):
        s = 'name : %s, text : %s, type : %s\n' % (self.field_name, self.field_value, self.type)
        if self.field_value and (self.type != 'boolean' and self.field_value.lower() in ('true', 'false')):
            raise ValueError('Type issue with %s' % s)

        if self.field_value and (self.type != 'integer' and self.field_value.isdigit()):
            raise ValueError('Type issue with %s' % s)

        return s


class XmlObjectError(Exception):
    pass


class XmlObject(object):
    def __init__(self, et, parent):
        self.parent = parent
        self.et = et
        self.fields = dict()

        self.connection = None
        self.scope = __name__
        self._id = None

    def get_level(self, current_level=0):
        if self.parent is None:
            return current_level
        else:
            return self.parent.get_level(current_level+1)

    def print_path(self, path=''):
        if self.parent is None:
            print self.__class__.__name__ + '/' + path
        else:
            return self.parent.print_path(self.__class__.__name__ + '/' + path)

    def get_id(self):
        # Cache to speed up DB queries
        if self._id is not None:
            return self._id

        # Query in-base, assuming no re-creation in the meantime
        name = self.get_name()
        if name is None:
            raise XmlObjectError('A name must be set.')

        cursor = self.connection.connection.cursor()
        sql_template = "select id from %s where %s = '%s'" % (self.sql_tablename, self.sql_namefield, name)
        sql_string = cursor.mogrify(sql_template)
        # print 'executing sql query : %s' % sql_string
        cursor.execute(sql_string)
        element = cursor.fetchone()

        if element is not None:
            id = int(element[0])
        else:
            id = None  # mean the object related to this name is not found on the database

        self._id = id
        return id

    def get_name(self):
        if self.xml_namefield is None:
            return ''

        if self.fields[self.xml_namefield].field_value is not None:
            return self.fields[self.xml_namefield].field_value.strip()
        else:
            raise XmlObjectError("%s name field is empty." % self.__class__.__name__)

    def empty(self):
        return len(self.fields) == 0

    def add_field(self, et):
        if not (et.tag in self.nested_attributes or et.tag in self.nested_attributes_list):
            self.fields[et.tag] = Field(et, self.get_field_type(et))

    def get_parent_name(self):
        if self.parent is None:
            return ''

        return self.parent.get_name()

    def get_parent_id(self):
        if self.parent is None:
            return None

        return self.parent.get_id()

    def get_parent(self):
        if self.parent is None:
            return None

        return self.parent

    def get_sql_fieldvalue(self, sql_fieldname):
        id = self.get_id()
        name = self.get_name()

        if name is None:
            return None

        cursor = self.connection.connection.cursor()
        sql_template = """
           select
               %s
           from
               %s
           where 
               %s = '%s'
        """ % (sql_fieldname, self.sql_tablename, self.sql_namefield, name)

        sql_string = cursor.mogrify(sql_template)
        # print 'executing sql query : %s' % sql_string
        cursor.execute(sql_string)
        element = cursor.fetchone()
        value = None
        if element is not None:
            if type(element[0]) == bool:
                value = element[0] and 'True' or 'False'

            if type(element[0]) == str:
                value = element[0]

            if type(element[0]) == int:
                value = str(element[0])
        else:
            value = None  # mean the object related to this name is not found on the database

        return value

    def clean_xml(self, xml_str_value):
        parser = etree.XMLParser(remove_blank_text=True)
        elem = etree.XML(xml_str_value, parser=parser)
        xml_str = etree.tostring(elem)
        data = etree.tostring(etree.fromstring(xml_str), pretty_print=True)
        return data

    def create_objects(self):
        if len(self.fields) == 0:
            return

        if self.get_id() is None:
            self.create()
        else:
            self.update()

    def create(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()


    def parse(self, connection):
        self.connection = connection
        for child in self.et:
            self.add_field(child)

        self.create_objects()
        for child in self.et:
            if child.tag in self.nested_attributes:
                o = dynamic_instanciation(child.tag, child, self, self.scope)
                o.parse(connection)

                setattr(self, child.tag, o)

            if child.tag in self.nested_attributes_list:
                setattr(self, child.tag, [])
                for nchild in child:
                    o = dynamic_instanciation(nchild.tag, nchild, self, self.scope)
                    o.parse(connection)
                    getattr(self, child.tag).append(o)

    def get_sql_field(self, field_name):
        sql_field_name = None
        if self.sql_fields.has_key(field_name):
            sql_field_name = self.sql_fields[field_name]
        else:
            raise ValueError('%s, cannot find sql mapping for XML field name : %s' % (self.sql_tablename, field_name))

        return sql_field_name
