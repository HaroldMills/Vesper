# Vesper Recorder README

This document describes how to install the Vesper Recorder on a Raspberry Pi, configure the recorder, and run it. It assumes that you start with an empty micro SD card on which you want to install the Raspberry Pi OS and the Vesper Recorder. I have tested these instructions using macOS to prepare the micro SD card, but not Windows or Linux. You'll need to modify the instructions a little for those platforms.

Note that if you're installing the Vesper Recorder to use on a more resource-constrained Raspberry Pi, some of the following may not work if you try to perform the installation on that machine. For example, I have had the first `conda` command of step 6 hang when I try to run it on a Raspberry Pi Zero 2 W, I suspect because that machine has only 512 MB of RAM. In this case I have found it effective to first install the micro SD card that I intend to use in the Raspberry Pi Zero 2 W in a different, less resource-constrained Raspberry Pi, for example a Raspberry Pi 400, and perform the software installation there. Once the software installation is complete, I then move the SD card to the Raspberry Pi Zero 2 W and use it there.


## 1. Install Raspberry Pi OS image onto micro SD card

Run the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on a computer that includes a micro SD card reader and follow the instructions in the imager to install the Raspberry Pi OS onto a micro SD card. I have used 128 GB SanDisk Extreme cards, just because that's what I've had around. I have always accepted the defaults for this step: I have not customized the installation.

Be sure to install a 64-bit version of the Rasberry Pi OS, since that is required by MiniForge. I do not recommend the Lite version, since in my experience it is missing some functionality that I like to have. For example, it seems to lack an ALSA audio capture volume control, and it also does not mount USB thumb drives automatically when they are inserted. I also do not recommend the Full version, since to me it seems bloated. The regular 64-bit Raspberry Pi OS, neither Full nor Lite, seems about right.


## 2. Boot Raspberry Pi from SD card

Install the micro SD card from the previous step in your Raspberry Pi, attach a keyboard, mouse, and monitor to the Pi, and boot it. The OS will ask you for a username and password to create a superuser account with, your Wi-Fi network and password, whether or not you want to install OS and application updates, etc.


## 3. Enable SSH access

* Change your Raspberry Pi's hostname (if you wish) in `Preferences -> Raspberry Pi Configuration -> System`. The default hostname is `raspberrypi`.

* Enable SSH for your Raspberry Pi in `Preferences -> Raspberry Pi Configuration -> Interfaces`.

* Reboot your Raspberry Pi.

* If you would like to allow ssh login without a password, put your RSA public key in `~/.ssh/authorized_keys`, for example by copying it from `~/.ssh/id_rsa.pub` on macOS. For details see [here](https://danidudas.medium.com/how-to-connect-to-raspberry-pi-via-ssh-without-password-using-ssh-keys-3abd782688a).


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
        conda install python-sounddevice h5py
        pip install -e .


## 7. Install AWS credential files

If you want the Vesper Recorder to interact with your AWS account, for example to upload recorded files to S3, install the necessary AWS `config` and `credentials` files in the `.aws` subdirectory of your home directory.


## 8. Install `flac` program

If you want the Vesper Recorder to record to FLAC files, install the [`flac` program](https://xiph.org/flac/documentation_tools_flac.html) from xiph.org with the following command:

        sudo apt install flac


## 9. Create and populate a Vesper Recorder home directory

* [Download](https://www.dropbox.com/scl/fi/qswv8hdolbis8x57l4inn/Vesper-Recorder-Home-Template.0.3.0a0.zip?rlkey=ycu1f6y84ytmlrss60proyml6&dl=1) the template Vesper Recorder home directory.

* Unzip the downloaded file anywhere you want, for example on your desktop. Unzipping the file should create a `Vesper Recorder` directory that contains the file `Vesper Recorder Settings.yaml`.

* Edit `Vesper Recorder Settings.yaml` for your use, according to the instructions in it.


## 10. Run the Vesper Recorder

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


## 11. Run the Vesper Recorder automatically on startup (optional)

If you would like to run the Vesper Recorder automatically on startup, you can create a Linux `systemd` service for the recorder and enable it as follows:

1. Edit the `vesper-recorder.service` and `run_vesper_recorder.sh` files that accompany this README and change all occurrences of `harold` to the name of the user you want to run the recorder.

2. Copy the modified `vesper-recorder.service` file into your Raspberry Pi's `/usr/lib/systemd/system` directory with:

        sudo cp vesper-recorder.service /usr/lib/systemd/system

3. Copy the modified `run_vesper_recorder.sh` into the `/usr/local/bin` directory with:

        sudo cp run_vesper_recorder.sh /usr/local/bin

4. Enable the new `vesper-recorder` service with:

        sudo systemctl enable vesper-recorder

The recorder should then start automatically when your Raspberry Pi does.

After you've installed the service, you can check its status at any time with:

        systemctl status vesper-recorder

You can also use the `systemctl` command to start, stop, enable, and disable the service. The commands for these operations are:

        sudo systemctl start vesper-recorder
        sudo systemctl stop vesper-recorder
        sudo systemctl enable vesper-recorder
        sudo systemctl disable vesper-recorder
