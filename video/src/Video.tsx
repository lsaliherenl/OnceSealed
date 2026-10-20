import React from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, Series, staticFile, useCurrentFrame } from "remotion";
import { Backdrop, Captions } from "./components";
import { SCENE_VIEWS } from "./scenes";
import { sans } from "./theme";
import { FPS, LEAD, type Scene, SCENES } from "./timing";

const SceneShell: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const View = SCENE_VIEWS[scene.id];
  const opacity = interpolate(frame, [0, 9, scene.frames - 7, scene.frames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity }}>
        <View />
      </AbsoluteFill>
      <Sequence from={Math.round(LEAD * FPS)} layout="none">
        <Audio src={staticFile(scene.audio)} />
      </Sequence>
      <Captions captions={scene.captions} />
    </AbsoluteFill>
  );
};

export const Video: React.FC = () => (
  <AbsoluteFill style={{ fontFamily: sans }}>
    <Backdrop />
    <Series>
      {SCENES.map((s) => (
        <Series.Sequence key={s.id} durationInFrames={s.frames} name={s.id}>
          <SceneShell scene={s} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
