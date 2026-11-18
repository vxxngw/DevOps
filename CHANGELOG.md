# Changelog

## [0.4.0](https://github.com/vxxngw/DevOps/compare/v0.3.0...v0.4.0) (2026-11-18)


### Features

* **ci:** Jenkins webhook deploys staging and waits for manual production approval ([#25](https://github.com/vxxngw/DevOps/issues/25)) ([8aadcaf](https://github.com/vxxngw/DevOps/commit/8aadcaf592999dcb1919a8da0b1569e3eb54a23e))
* **compose:** make docker compose up work without a pre-generated .env ([#29](https://github.com/vxxngw/DevOps/issues/29)) ([ff2cd81](https://github.com/vxxngw/DevOps/commit/ff2cd81a8ae202edf0732a4a86807ec414545957))

## [0.3.0](https://github.com/vxxngw/DevOps/compare/v0.2.0...v0.3.0) (2026-11-18)


### Features

* **infra:** Linux baseline on a VirtualBox lab VM (Bài 3) ([#18](https://github.com/vxxngw/DevOps/issues/18)) ([e896161](https://github.com/vxxngw/DevOps/commit/e8961618f8617b7158684e15c57dead9557d4289))
* **infra:** provision k3s, Docker and Jenkins agent with Ansible on VirtualBox ([#21](https://github.com/vxxngw/DevOps/issues/21)) ([eb3748b](https://github.com/vxxngw/DevOps/commit/eb3748bcd02d7c9ed0df5f56ddba4cd585fd841c))
* task baolong ([#17](https://github.com/vxxngw/DevOps/issues/17)) ([9f4a4c3](https://github.com/vxxngw/DevOps/commit/9f4a4c3d869a57512d32db399bdc712c60071115))


### Bug Fixes

* **infra:** make entry shell scripts executable for systemd ([#20](https://github.com/vxxngw/DevOps/issues/20)) ([9c2c897](https://github.com/vxxngw/DevOps/commit/9c2c8973ebcaebc07ea35aeb99f7a39d2c751a42))

## [0.2.0](https://github.com/vxxngw/DevOps/compare/v0.1.0...v0.2.0) (2026-11-18)


### Features

* **observability:** run monitoring stack and deliver alerts to Discord ([#12](https://github.com/vxxngw/DevOps/issues/12)) ([ac69934](https://github.com/vxxngw/DevOps/commit/ac6993402395b313effcda926a3c71e302c96a41))

## 0.1.0 (2026-11-18)


### Features

* bootstrap An Uyen Hospital appointment platform ([b4d0fbc](https://github.com/vxxngw/DevOps/commit/b4d0fbc6c17ca0dab5833d234ffcf0cedc28a34e))
* **ci:** verify SHA stack and record live Jenkins gates ([5bf6734](https://github.com/vxxngw/DevOps/commit/5bf673411fa75b726832d1363cb7d147bbceadcd))
* **devops:** prepare observability and restore authenticated Jenkins ([7c14a27](https://github.com/vxxngw/DevOps/commit/7c14a27fb6cf621f4e5c0a3f9c4b8136656af687))
* **infra:** prepare three-VM k3s lab and deployment gates ([cd941d3](https://github.com/vxxngw/DevOps/commit/cd941d319021365ac491fd4acb2326a7b9fe6dbb))
* **observability:** prepare monitoring alerts and EFK stack ([3b2189d](https://github.com/vxxngw/DevOps/commit/3b2189de98ccc2843aaa560071ab75d6e77f0e98))
* **scripts:** add init-env.mjs helper for nodejs ([ce6fe39](https://github.com/vxxngw/DevOps/commit/ce6fe39f72cedd094a893d9ea9e1ccb442f5a07a))


### Bug Fixes

* **ci:** include engine hostname in Docker TLS certificate ([9347bb8](https://github.com/vxxngw/DevOps/commit/9347bb86b3a0a0ca54f40ddadab961f009b5393a))
* **ci:** retain Jenkins ownership across source and repository moves ([32f4343](https://github.com/vxxngw/DevOps/commit/32f4343f8bb800053faf81bfce1d171b3fcbf697))
* **ci:** validate restored Jenkins and preserve scan failure gates ([955eff1](https://github.com/vxxngw/DevOps/commit/955eff1956178cb9f39c888e4329dd67d535f461))
* **infra:** repair source paths and verify dev backup restore ([0bd3fb3](https://github.com/vxxngw/DevOps/commit/0bd3fb303f50999a54d08648f2c7d9a83edc6188))
* **security:** replace vulnerable container bases ([4a6e056](https://github.com/vxxngw/DevOps/commit/4a6e05647044ad8722771eb0ba8bbe763b2133b1))
