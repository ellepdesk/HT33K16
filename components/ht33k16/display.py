import esphome.codegen as cg
from esphome.components import display, i2c
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_INTENSITY, CONF_LAMBDA

DEPENDENCIES = ["i2c"]

ht33k16_ns = cg.esphome_ns.namespace("ht33k16")
HT33K16Component = ht33k16_ns.class_(
    "HT33K16Component", cg.PollingComponent, i2c.I2CDevice
)
HT33K16ComponentRef = HT33K16Component.operator("ref")


CONFIG_SCHEMA = (
    display.BASIC_DISPLAY_SCHEMA.extend(
        {
            cv.GenerateID(): cv.declare_id(HT33K16Component),
            cv.Optional(CONF_INTENSITY, default=15): cv.int_range(min=0, max=15),
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(i2c.i2c_device_schema(0x70))
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await display.register_display(var, config)
    await i2c.register_i2c_device(var, config)

    cg.add(var.set_intensity(config[CONF_INTENSITY]))

    if CONF_LAMBDA in config:
        lambda_ = await cg.process_lambda(
            config[CONF_LAMBDA], [(HT33K16ComponentRef, "it")], return_type=cg.void
        )
        cg.add(var.set_writer(lambda_))
