from scalecodec.base import ScaleBytes
from scalecodec.types import U8, U16, U32, U64, U128, U256


def process_encode(self, value):  # noqa: C901
    data = ScaleBytes(bytearray())

    value = value or []

    if self.runtime_config.get_decoder_class(self.sub_type) is U8:
        # u8 arrays are represented as bytes or hex-bytes (e.g. [u8; 3] as 0x123456)
        if type(value) is str and value[0:2] == '0x':
            value = bytes.fromhex(value[2:])

        if type(value) is list:
            value = bytes(value)

        if type(value) is not bytes:
            print(self.runtime_config.get_decoder_class(self.sub_type))
            print(value)
            raise ValueError('Value should a hex-string (0x..) or bytes')

        if len(value) != self.element_count:
            raise ValueError('Value should be {} bytes long'.format(self.element_count))

        return ScaleBytes(value)

    else:
        if type(value) is str:
            if value[0:2] != '0x':
                raise ValueError('Give the value is not from 0x')
            elif self.runtime_config.get_decoder_class(self.sub_type) is U16 and len(value[2:]) != self.element_count * 4:
                raise ValueError('Value should be {} bytes long'.format(self.element_count))
            elif self.runtime_config.get_decoder_class(self.sub_type) is U32 and len(value[2:]) != self.element_count * 8:
                raise ValueError('Value should be {} bytes long'.format(self.element_count))
            elif self.runtime_config.get_decoder_class(self.sub_type) is U64 and len(value[2:]) != self.element_count * 16:
                raise ValueError('Value should be {} bytes long'.format(self.element_count))
            elif self.runtime_config.get_decoder_class(self.sub_type) is U128 and len(value[2:]) != self.element_count * 32:
                raise ValueError('Value should be {} bytes long'.format(self.element_count))
            elif self.runtime_config.get_decoder_class(self.sub_type) is U256 and len(value[2:]) != self.element_count * 64:
                raise ValueError('Value should be {} bytes long'.format(self.element_count))
            else:
                return ScaleBytes(value)

        if not type(value) is list:
            print(value)
            raise ValueError('Given value is not a list')

        for element_value in value:
            element_obj = self.runtime_config.create_scale_object(
                type_string=self.sub_type, metadata=self.metadata
            )
            data += element_obj.encode(element_value)

        return data
