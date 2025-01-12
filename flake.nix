{
  description = "GameBoy emulator written in RPython";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/release-24.11";
    flake-utils.url = "github:numtide/flake-utils";
    rpypkgs = {
      url = "github:rpypkgs/rpypkgs";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
  };

  outputs = { self, nixpkgs, flake-utils, rpypkgs }:
    let
      # The systems where RPython has been tested to work.
      testedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in flake-utils.lib.eachSystem testedSystems (system:
      let
        pkgs = import nixpkgs { inherit system; };
        interp = rpypkgs.lib.${system}.mkRPythonDerivation {
          entrypoint = "pygirl/targetgbimplementation.py";
          binName = "targetgbimplementation-c";
          binInstallName = "pygirl";
          optLevel = "2";
          withLibs = ls: [ ls.rsdl ];
        } {
          pname = "pygirl";
          version = "16.11";

          src = ./.;

          buildInputs = with pkgs; [ SDL SDL2 ];

          # XXX shipped without license, originally same license as PyPy
          meta = {
            description = "GameBoy emulator written in RPython";
            license = pkgs.lib.licenses.mit;
          };
        };
      in {
        packages.default = interp;
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [ unzip ];
        };
      }
    );
}
