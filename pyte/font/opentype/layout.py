
from .tables import OpenTypeTable, MultiFormatTable, context_array, offset_array
from .parse import fixed, array, uint16, tag, glyph_id, offset, indirect, Packed


class Record(OpenTypeTable):
    entries = [('Tag', tag),
               ('Offset', offset)]

    def parse_value(self, file, file_offset, entry_type):
        self['Value'] = entry_type(file, file_offset + self['Offset'])


class ListTable(OpenTypeTable):
    entry_type = None
    entries = [('Count', uint16),
               ('Record', context_array(Record, 'Count'))]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        for record in self['Record']:
            record.parse_value(file, file_offset, self.entry_type)


class LangSysTable(OpenTypeTable):
    entries = [('LookupOrder', offset),
               ('ReqFeatureIndex', uint16),
               ('FeatureCount', uint16),
               ('FeatureIndex', context_array(uint16, 'FeatureCount'))]


class ScriptTable(ListTable):
    entry_type = LangSysTable
    entries = [('DefaultLangSys', indirect(LangSysTable))] + ListTable.entries


class ScriptListTable(ListTable):
    entry_type = ScriptTable


class FeatureTable(OpenTypeTable):
    entries = [('FeatureParams', offset),
               ('LookupCount', uint16),
               ('LookupListIndex', context_array(uint16, 'LookupCount'))]

    def __init__(self, file, offset):
        super().__init__(file, offset)
        if self['FeatureParams']:
            # TODO: parse Feature Parameters
            pass
        else:
            del self['FeatureParams']


class FeatureListTable(ListTable):
    entry_type = FeatureTable


class LookupFlag(Packed):
    reader = uint16
    fields = [('RightToLeft', 0x0001, bool),
              ('IgnoreBaseGlyphs', 0x0002, bool),
              ('IgnoreLigatures', 0x0004, bool),
              ('IgnoreMarks', 0x0008, bool),
              ('UseMarkFilteringSet', 0x010, bool),
              ('MarkAttachmentType', 0xFF00, int)]


class RangeRecord(OpenTypeTable):
    entries = [('Start', glyph_id),
               ('End', glyph_id),
               ('StartCoverageIndex', uint16)]


class Coverage(MultiFormatTable):
    entries = [('CoverageFormat', uint16)]
    formats = {1: [('GlyphCount', uint16),
                   ('GlyphArray', context_array(glyph_id, 'GlyphCount'))],
               2: [('RangeCount', uint16),
                   ('RangeRecord', context_array(RangeRecord, 'RangeCount'))]}


class ClassRangeRecord(OpenTypeTable):
    entries = [('Start', glyph_id),
               ('End', glyph_id),
               ('Class', uint16)]


class ClassDefinition(MultiFormatTable):
    entries = [('ClassFormat', uint16)]
    formats = {1: [('StartGlyph', glyph_id),
                   ('GlyphCount', uint16),
                   ('ClassValueArray', context_array(uint16, 'GlyphCount'))],
               2: [('ClassRangeCount', uint16),
                   ('ClassRangeRecord', context_array(ClassRangeRecord,
                                                      'ClassRangeCount'))]}


class LookupTable(OpenTypeTable):
    entries = [('LookupType', uint16),
               ('LookupFlag', LookupFlag),
               ('SubTableCount', uint16)]

    def __init__(self, file, file_offset, subtable_types):
        super().__init__(file, file_offset)
        offsets = array(uint16, self['SubTableCount'])(file)
        if self['LookupFlag']['UseMarkFilteringSet']:
            self['MarkFilteringSet'] = uint16(file)
        subtable_type = subtable_types[self['LookupType']]
        self['SubTable'] = [subtable_type(file, file_offset + subtable_offset)
                            for subtable_offset in offsets]


class LookupListTable(OpenTypeTable):
    entries = [('LookupCount', uint16)]

    def __init__(self, file, file_offset, types):
        super().__init__(file, file_offset)
        lookup_offsets = array(offset, self['LookupCount'])(file)
        self['Lookup'] = [LookupTable(file, file_offset + lookup_offset, types)
                          for lookup_offset in lookup_offsets]


class LayoutTable(OpenTypeTable):
    entries = [('Version', fixed),
               ('ScriptList', indirect(ScriptListTable)),
               ('FeatureList', indirect(FeatureListTable))]

    def __init__(self, file, file_offset):
        super().__init__(file, file_offset)
        lookup_list_offset = offset(file)
        self['LookupList'] = LookupListTable(file,
                                             file_offset + lookup_list_offset,
                                             self.lookup_types)