from aws_cdk import core

from stacks.synth import synth_stacks


def build():
    app = core.App()
    synth_stacks(app)
    app.synth()


build()

