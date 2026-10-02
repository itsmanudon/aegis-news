from temporalio import activity


@activity.defn(name="foundation_echo")
async def foundation_echo(name: str) -> str:
    activity.logger.info("foundation_activity_completed")
    return f"AegisNews foundation: {name}"
