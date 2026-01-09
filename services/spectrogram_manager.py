"""
Spectrogram Manager

This service provides functionality to generate mel spectrograms from audio files
for bird call classification. It uses librosa for audio processing and matplotlib
for image generation.

Spectrograms are saved as PNG images suitable for machine learning workflows.
"""

import librosa
import librosa.display
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Optional, Tuple
from pathlib import Path
import json


class SpectrogramManager:
    """Service for generating mel spectrograms from audio files."""
    
    # Default parameters for bird call spectrograms
    DEFAULT_PARAMS = {
        'n_fft': 2048,          # Window size for FFT
        'hop_length': 512,      # Overlap between windows
        'n_mels': 128,          # Number of mel filter banks
        'fmin': 0,              # Minimum frequency (Hz)
        'fmax': 8000,           # Maximum frequency (Hz) - bird calls typically 0-8kHz
        'sr': 22050,            # Target sample rate (librosa default)
        'dpi': 100,             # Image resolution
        'figsize': (10, 4)      # Figure size in inches (width, height)
    }
    
    def __init__(self, default_params: Optional[Dict] = None):
        """
        Initialize the spectrogram manager.
        
        Args:
            default_params: Optional dictionary to override default parameters
        """
        self.params = default_params or self.DEFAULT_PARAMS.copy()
    
    def get_default_params(self) -> Dict:
        """
        Get default spectrogram parameters.
        
        Returns:
            Dictionary of default parameters
        """
        return self.params.copy()
    
    def load_audio(
        self,
        audio_path: str,
        sr: Optional[int] = None,
        duration: Optional[float] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio file using librosa.
        
        Args:
            audio_path: Path to audio file (supports MP3, WAV, etc.)
            sr: Target sample rate (None uses librosa default or file's native rate)
            duration: Optional maximum duration to load (in seconds)
        
        Returns:
            Tuple of (audio_array, sample_rate)
        
        Raises:
            Exception: If audio file cannot be loaded
        """
        target_sr = sr or self.params.get('sr', 22050)
        
        try:
            y, sr_loaded = librosa.load(
                audio_path,
                sr=target_sr,
                duration=duration
            )
            return y, sr_loaded
        except Exception as e:
            raise Exception(f"Failed to load audio from {audio_path}: {e}")
    
    def generate_mel_spectrogram(
        self,
        audio_path: str,
        output_path: str,
        **kwargs
    ) -> Dict:
        """
        Generate mel spectrogram from audio file and save as PNG image.
        
        Args:
            audio_path: Path to input audio file
            output_path: Path to save spectrogram image (PNG)
            **kwargs: Optional parameters to override defaults:
                - n_fft: FFT window size
                - hop_length: Hop length between windows
                - n_mels: Number of mel filter banks
                - fmin: Minimum frequency
                - fmax: Maximum frequency
                - sr: Sample rate
                - dpi: Image DPI
                - figsize: Figure size (width, height)
        
        Returns:
            Dictionary with spectrogram metadata:
                - image_width: Image width in pixels
                - image_height: Image height in pixels
                - sample_rate: Audio sample rate
                - duration_seconds: Audio duration
                - spectrogram_params: JSON string of parameters used
        
        Raises:
            Exception: If spectrogram generation fails
        """
        # Merge parameters (kwargs override defaults)
        params = self.params.copy()
        params.update(kwargs)
        
        # Load audio
        y, sr = self.load_audio(audio_path, sr=params.get('sr'))
        duration = len(y) / sr
        
        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=params['n_fft'],
            hop_length=params['hop_length'],
            n_mels=params['n_mels'],
            fmin=params['fmin'],
            fmax=params['fmax']
        )
        
        # Convert to decibels (log scale)
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Create figure
        fig, ax = plt.subplots(figsize=params['figsize'], dpi=params['dpi'])
        
        # Display spectrogram
        img = librosa.display.specshow(
            mel_spec_db,
            x_axis='time',
            y_axis='mel',
            sr=sr,
            fmin=params['fmin'],
            fmax=params['fmax'],
            hop_length=params['hop_length'],
            ax=ax
        )
        
        # Remove axes and labels for cleaner ML-ready images
        ax.axis('off')
        plt.tight_layout(pad=0)
        
        # Save figure
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(
            output_path,
            format='png',
            bbox_inches='tight',
            pad_inches=0,
            dpi=params['dpi']
        )
        plt.close(fig)
        
        # Get image dimensions
        from PIL import Image
        with Image.open(output_path) as img:
            image_width, image_height = img.size
        
        # Prepare parameters dict for metadata
        params_for_metadata = {
            'n_fft': params['n_fft'],
            'hop_length': params['hop_length'],
            'n_mels': params['n_mels'],
            'fmin': params['fmin'],
            'fmax': params['fmax'],
            'sr': sr,
            'dpi': params['dpi'],
            'figsize': params['figsize']
        }
        
        return {
            'image_width': image_width,
            'image_height': image_height,
            'sample_rate': sr,
            'duration_seconds': duration,
            'spectrogram_params': json.dumps(params_for_metadata)
        }
    
    def generate_mel_spectrogram_from_array(
        self,
        y: np.ndarray,
        sr: int,
        output_path: str,
        **kwargs
    ) -> Dict:
        """
        Generate mel spectrogram from audio array (already loaded).
        
        Args:
            y: Audio time series array
            sr: Sample rate
            output_path: Path to save spectrogram image
            **kwargs: Optional parameters (same as generate_mel_spectrogram)
        
        Returns:
            Dictionary with spectrogram metadata
        """
        # Merge parameters
        params = self.params.copy()
        params.update(kwargs)
        params['sr'] = sr  # Use provided sample rate
        
        duration = len(y) / sr
        
        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=params['n_fft'],
            hop_length=params['hop_length'],
            n_mels=params['n_mels'],
            fmin=params['fmin'],
            fmax=params['fmax']
        )
        
        # Convert to decibels
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Create figure
        fig, ax = plt.subplots(figsize=params['figsize'], dpi=params['dpi'])
        
        # Display spectrogram
        librosa.display.specshow(
            mel_spec_db,
            x_axis='time',
            y_axis='mel',
            sr=sr,
            fmin=params['fmin'],
            fmax=params['fmax'],
            hop_length=params['hop_length'],
            ax=ax
        )
        
        # Remove axes for ML-ready images
        ax.axis('off')
        plt.tight_layout(pad=0)
        
        # Save figure
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(
            output_path,
            format='png',
            bbox_inches='tight',
            pad_inches=0,
            dpi=params['dpi']
        )
        plt.close(fig)
        
        # Get image dimensions
        from PIL import Image
        with Image.open(output_path) as img:
            image_width, image_height = img.size
        
        # Prepare parameters for metadata
        params_for_metadata = {
            'n_fft': params['n_fft'],
            'hop_length': params['hop_length'],
            'n_mels': params['n_mels'],
            'fmin': params['fmin'],
            'fmax': params['fmax'],
            'sr': sr,
            'dpi': params['dpi'],
            'figsize': params['figsize']
        }
        
        return {
            'image_width': image_width,
            'image_height': image_height,
            'sample_rate': sr,
            'duration_seconds': duration,
            'spectrogram_params': json.dumps(params_for_metadata)
        }

