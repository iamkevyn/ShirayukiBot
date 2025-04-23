 pkgs }: {
  deps = [
    pkgs.python311Full
    pkgs.ffmpeg
    pkgs.libsodium
    pkgs.opus      # ✅ Biblioteca necessária pro áudio do Discord
  ];
}