import { Config } from "@remotion/cli/config";
import os from "os";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setConcurrency(Math.min(2, os.cpus().length));
