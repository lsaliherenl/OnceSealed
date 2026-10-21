import React from "react";
import { Composition, Still } from "remotion";
import { Thumbnail } from "./Thumbnail";
import { FPS, HEIGHT, TOTAL_FRAMES, WIDTH } from "./timing";
import { Video } from "./Video";

export const Root: React.FC = () => (
  <>
    <Composition id="OnceSealed" component={Video} durationInFrames={TOTAL_FRAMES} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Still id="Thumbnail" component={Thumbnail} width={1280} height={720} />
  </>
);
