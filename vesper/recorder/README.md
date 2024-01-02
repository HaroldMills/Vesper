# Vesper Recorder README

This document describes how to install the Vesper Recorder on a Raspberry Pi, configure the recorder, and run it. It assumes that you start with an empty micro SD card on which you want to install the Raspberry Pi OS and the Vesper Recorder. I have tested these instructions using macOS to prepare the micro SD card, but not Windows or Linux. You'll need to modify the instructions a little for those platforms.

## 1. Install Raspberry Pi OS image onto micro SD card

Run the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on a computer that includes a micro SD card reader and follow the instructions in the imager to install the Raspberry Pi OS onto a micro SD card. I have used 128 GB SanDisk Extreme cards, just because that's what I've had around. I have always accepted the defaults for this step: I have not customized the installation.


## 2. Boot Raspberry Pi from SD card

Install the micro SD card from the previous step in your Raspberry Pi, attach a keyboard, mouse, and monitor to the Pi, and boot it. The OS will ask you for a username and password to create a superuser account with, your Wi-Fi network and password, whether or not you want to install OS and application updates, etc.


## 3. Enable SSH access

* Change your Raspberry Pi's hostname (if you wish) in `System -> Raspberry Pi Configuration -> System`. The default hostname is `raspberrypi`.

* Enable SSH for your Raspberry Pi in `System -> Raspberry Pi Configuration -> Interfaces`.

* Reboot your Raspberry Pi.

* If you would like to allow ssh login without a password, put your RSA public key in `~/.ssh/authorized_keys`, for example by copying it from `~/.ssh/id_rsa.pub` on macOS. For details see [here](https://danidudas.medium.com/how-to-connect-to-raspberry-pi-via-ssh-without-password-using-ssh-keys-3abd782688a). Also consider doing a `chmod 700 .ssh` to allow only your user access to the .ssh directory.


## 4. Install MiniForge

* Download the miniforge installer for the `aarch64 (arm64)` architecture from [here](https://github.com/conda-forge/miniforge). The installer is a large file named "Miniforge3-Linux-aarch64.sh" or something similar.

* Run the installer in a terminal in the download directory with `bash <installer file name>`. Accept the defaults for the installation, including installation in the `~/miniforge3` directory. After the installation, the installer will offer to run `conda init` for you. Accept the offer.

* After installation is complete, close your terminal and open a fresh one to ensure that subsequent `conda` commands will work correctly.


## 5. Clone Vesper Git repository from GitHub

* In a terminal, `cd` to the directory into which you would like to clone the Vesper Git repo. The repo will appear within that directory as the `Vesper` subdirectory.

* Issue the following command:

        git clone https://github.com/HaroldMills/Vesper.git


## 6. Create vesper-recorder environment

* In a terminal, `cd` to your Vesper Git repo directory, i.e. the one named `Vesper` that you created in the previous section.

* Issue the following commands:

        conda create -n vesper-recorder python=3.11
        conda activate vesper-recorder
        conda install python-sounddevice
        pip install -e .


## 7. Install AWS credential files

If you want the Vesper Recorder to interact with your AWS account, for example to upload recorded files to S3, install the necessary AWS `config` and `credentials` files in the `.aws` subdirectory of your home directory.


## 8. Create and populate a Vesper Recorder home directory

* [Download](https://www.dropbox.com/scl/fi/qswv8hdolbis8x57l4inn/Vesper-Recorder-Home-Template.0.3.0a0.zip?rlkey=ycu1f6y84ytmlrss60proyml6&dl=1) the template Vesper Recorder home directory.

* Unzip the downloaded file anywhere you want, for example on your desktop. Unzipping the file should create a `Vesper Recorder` directory that contains the file `Vesper Recorder Settings.yaml`.

* Edit `Vesper Recorder Settings.yaml` for your use, according to the instructions in it.


## 9. Run the Vesper Recorder

To run the Vesper Recorder:

* SSH into your Raspberry Pi from another computer with a command of the form:

        ssh <username>@<raspberry pi hostname>

  where `<username>` is the name of the superuser you created for your Raspberry Pi OS and `<hostname>` is your Raspberry Pi hostname (`raspberrypi` by default), for example:

        ssh vesper@raspberrypi

* At the SSH prompt, cd to the Vesper Recorder home directory and issue the following commands to run the Vesper Recorder:

        conda activate vesper-recorder
        nohup vesper_recorder &

  It is important to run the recorder using `nohup` to ensure that the recorder doesn't quit when you close your SSH connection.

* Verify that the Vesper Recorder is running and properly configured by visiting its web page at `<hostname>:8000` (for example, `raspberrypi:8000` for the default hostname) in a web browser on another computer.

* Close your SSH connection to your Raspberry Pi by typing `Ctrl-D` at the SSH prompt.
