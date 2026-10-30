import itertools


from vesper.django.app.models import (
    Clip, StringAnnotation, StringAnnotationEdit, Tag, TagEdit)


class BatchClipCreator:

    """
    Receives clips to be created one by one but creates them in batches.

    Call the `add_clip` method with clips to be created. When the number
    of added clips reaches the batch size, they are created in the
    database. Call the `flush` method after your last call to `add_clip`
    to create the clips of the current batch.
    """


    def __init__(self, batch_size=50):
        self._batch_size = batch_size
        self._clips = []
        self._annos = []
        self._tags = []


    def add_clip(self, clip, annotations=None, tags=None):

        self._clips.append(clip)

        if annotations is not None:
            self._annos.append(annotations)

        if tags is not None:
            self._tags.append(tags)

        if len(self._clips) == self._batch_size:
            self.flush()


    def flush(self):

        if len(self._clips) != 0:
            # there are clips to create

            # Create clips.
            Clip.objects.bulk_create(self._clips)

            if len(self._annos) != 0:
                # there are annotations to create

                # Flatten annotation list.
                annos = list(itertools.chain.from_iterable(self._annos))

                # Create annotations.
                StringAnnotation.objects.bulk_create(annos)

                # Create annotation edits.
                edits = [
                    StringAnnotationEdit(
                        action=StringAnnotationEdit.ACTION_SET,
                        clip=a.clip,
                        info=a.info,
                        value=a.value,
                        creation_time=a.creation_time,
                        creating_job=a.creating_job,
                        creating_processor=a.creating_processor)
                    for a in annos]
                StringAnnotationEdit.objects.bulk_create(edits)

                # Clear annotation list for next batch.
                self._annos.clear()

            if len(self._tags) != 0:
                # there are tags to create

                # Flatten tag list.
                tags = list(itertools.chain.from_iterable(self._tags))

                # Create tags.
                Tag.objects.bulk_create(tags)

                # Create tag edits.
                edits = [
                    TagEdit(
                        action=TagEdit.ACTION_SET,
                        clip=t.clip,
                        info=t.info,
                        creation_time=t.creation_time,
                        creating_job=t.creating_job,
                        creating_processor=t.creating_processor)
                    for t in tags]
                TagEdit.objects.bulk_create(edits)

                # Clear tag list for next batch.
                self._tags.clear()

            # Clear clip list for next batch.
            self._clips.clear()
