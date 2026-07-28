from tools.mumu_client import MuMuRemoteClient

class MuMuExecutor:
    def __init__(
        self,
        host="127.0.0.1",
        port=5000
    ):

        self.client = MuMuRemoteClient(
            host=host,
            port=port
        )


    def screenshot(self,name):
        result = self.client.execute_batch(
            [
                {
                    "action":"SCREENSHOT",
                    "coordinates":[],
                    "text":name
                }
            ]
        )

        return result

    def execute(
        self,
        action
    ):

        return self.client.execute_batch([action])