import {Composition} from 'remotion';
import {CutVideo, CutVideoProps, defaultProps} from './CutVideo';

export const Root: React.FC = () => {
  return (
    <Composition
      id="CutVideo"
      component={CutVideo}
      defaultProps={defaultProps}
      // Placeholder values; the real fps/dimensions/duration come from the
      // cutlist via calculateMetadata — locked to the probed source (hard rule).
      fps={30}
      width={1920}
      height={1080}
      durationInFrames={300}
      calculateMetadata={({props}) => {
        const p = props as CutVideoProps;
        const totalSeconds = p.segments.reduce(
          (sum, s) => sum + (s.end - s.start),
          0,
        );
        return {
          fps: p.fps,
          width: p.width,
          height: p.height,
          durationInFrames: Math.max(1, Math.round(totalSeconds * p.fps)),
        };
      }}
    />
  );
};
