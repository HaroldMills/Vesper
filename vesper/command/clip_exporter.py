class ClipExporter:


    clip_query_set_select_related_args = None

    
    def begin_exports(self):
        pass


    def begin_subset_exports(
            self, station, mic_output, date, detector, clip_count):
        pass


    def export(self, clip):
        pass


    def end_subset_exports(self):
        pass


    def end_exports(self):
        pass
