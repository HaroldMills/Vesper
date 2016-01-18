"""Provides access to the extensions of a program."""


from __future__ import print_function


# TODO: Use a hierarchical name space for extensions?


# TODO: Don't hard-code extensions. They should specified from outside
# somehow. One possibility is that they could be specified in plug-in
# manifest files. It would also be desirable to be able to specify
# different subsets of installed extensions to work with at different
# times, say for different analysis projects.


_extensions = None


def get_extensions(extension_point_name):
    _initialize_if_needed()
    extensions = _extensions.get(extension_point_name, ())
    return dict((e.name, e) for e in extensions)
    
    
def _initialize_if_needed():
    if _extensions is None:
        load_extensions()
        
        
def load_extensions():
    
    # These imports are here rather than at top level to avoid circular
    # import problems.
    from mpg_ranch.bat_importer import BatImporter as MpgRanchBatImporter
    from mpg_ranch.clips_csv_exporter \
        import ClipsCsvExporter as MpgRanchClipsCsvExporter
    from mpg_ranch.nfc_importer import NfcImporter as MpgRanchNfcImporter
    from mpg_ranch.outside_clip_classifier \
        import OutsideClipClassifier as MpgRanchOutsideClipClassifier
    from mpg_ranch.nfc_species_classifier import NfcSpeciesClassifier
    from old_bird.detector import Detector as OldBirdDetector
    from vesper.vcl.classify_command import ClassifyCommand
    from vesper.vcl.clips_exporter import ClipsExporter
    from vesper.vcl.create_command import CreateCommand
    from vesper.vcl.detect_command import DetectCommand
    from vesper.vcl.export_command import ExportCommand
    from vesper.vcl.help_command import HelpCommand
    from vesper.vcl.import_command import ImportCommand
    from vesper.vcl.nfc_coarse_classifier import NfcCoarseClassifier
    from vesper.vcl.sample_command import SampleCommand

    global _extensions
    
    _extensions = {
            
        'VCL Classifier': (
            MpgRanchOutsideClipClassifier,
            NfcCoarseClassifier,
            NfcSpeciesClassifier,
        ),
        
        'VCL Command': (
            ClassifyCommand,
            CreateCommand,
            DetectCommand,
            ExportCommand,
            HelpCommand,
            ImportCommand,
            SampleCommand,
        ),
        
        'VCL Detector': (
            OldBirdDetector,
        ),
                   
        'VCL Exporter': (
            ClipsExporter,
            MpgRanchClipsCsvExporter,
        ),
                   
        'VCL Importer': (
            MpgRanchBatImporter,
            MpgRanchNfcImporter,
        )
            
    }
