import h5py

from vesper.util.bunch import Bunch
import vesper.util.numpy_utils as numpy_utils


class ClipsHdf5File:
    
    
    def __init__(self, file_path):
        self._file_path = file_path
        
        
    def get_num_clips(self):
        with h5py.File(self._file_path) as f:
            group = f['clips']
            return len(group)
        
        
    def get_sample_rate(self):
        with h5py.File(self._file_path) as f:
            return f['clips'].attrs['sample_rate']
 
    
    def read_clips(
            self, max_num_clips=None, notification_period=None, listener=None):
        
        with h5py.File(self._file_path) as f:
            
            group = f['clips']
            
            total_num_clips = len(group)
            
            if max_num_clips is not None:
                num_clips = min(max_num_clips, total_num_clips)
            else:
                num_clips = total_num_clips
                
            clips = []
                
            if num_clips == total_num_clips:
                # getting all clips
                
                for i, dataset in enumerate(group.values()):
                    
                    if notification_period is not None and \
                            i != 0 and i % notification_period == 0:
                        listener(i)
                        
                    clip = self._create_clip(dataset)
                    clips.append(clip)
                    
            else:
                # not getting all clips
                
                keys = numpy_utils.reproducible_choice(
                    list(group.keys()), num_clips, replace=False)
                
                for i, key in enumerate(keys):
                    
                    if notification_period is not None and \
                            i != 0 and i % notification_period == 0:
                        listener(i)
                        
                    dataset = group[key]
                    clip = self._create_clip(dataset)
                    clips.append(clip)
                    
        clips.sort(key=lambda c: c.id)
        
        return clips
                
                
    def _create_clip(self, dataset):
                    
        attrs = dataset.attrs
        
        return Bunch(
            id=attrs['id'],
            waveform=dataset[:],
            station=attrs['station'],
            microphone=attrs['microphone'],
            detector=attrs['detector'],
            night=attrs['night'],
            start_time=attrs['start_time'],
            original_sample_rate=attrs['original_sample_rate'],
            classification=attrs['classification']
        )
