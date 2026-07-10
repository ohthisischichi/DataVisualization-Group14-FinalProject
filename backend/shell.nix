{ pkgs ? import <nixpkgs> {config.allowUnfree = true;} }:

let
  dynamic-libs = with pkgs; [
    stdenv.cc.cc.lib # Provides libstdc++.so.6 (crucial for TensorFlow/Keras/Numpy)
    zlib             # Used for data compression
    glib             # Common dependency for underlying C libraries
    freetype         # Needed by wordcloud to render fonts
    libjpeg          # Needed by image processing libraries
  ];
in
pkgs.mkShell {
  packages = with pkgs; [
    # Python Environment
    python3
    python3Packages.pip
    python3Packages.virtualenv

    gcc
    gnumake

    ngrok
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath dynamic-libs}:$LD_LIBRARY_PATH"

    if [ ! -d ".venv" ]; then
      echo "Creating venv..."
      python -m venv .venv
    fi

    # 4. Activate the environment
    source .venv/bin/activate

    # 5. Install the requirements
    if [ -f "requirements.txt" ]; then
      echo "Downloading requirements.txt..."
      # Using --prefer-binary prevents pip from trying to compile heavy ML packages from source
      pip install --prefer-binary -r requirements.txt
    fi

    echo "Environment done"
    
    # Export the path for PyTorch to talk to GPU
    export LD_LIBRARY_PATH=/run/opengl-driver/lib:${pkgs.linuxPackages.nvidia_x11}/lib:$LD_LIBRARY_PATH     
  '';
}
