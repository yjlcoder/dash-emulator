from dash_emulator.scheduler import SchedulerEventHandler


class EventLogger(SchedulerEventHandler):
    def on_segment_download_start(self, index, selections):
        print("Download start. Index: %d, Selections: %s" % (index, str(selections)))

    def on_segment_download_complete(self, index):
        print("Download complete. Index: %d" % (index))
