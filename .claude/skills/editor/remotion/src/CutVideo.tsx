import {AbsoluteFill, OffthreadVideo, Sequence, staticFile} from 'remotion';

export type Segment = {start: number; end: number};

export type CutVideoProps = {
  src: string;
  fps: number;
  width: number;
  height: number;
  segments: Segment[];
};

export const defaultProps: CutVideoProps = {
  src: 'source.mp4',
  fps: 30,
  width: 1920,
  height: 1080,
  segments: [{start: 0, end: 10}],
};

export const CutVideo: React.FC<CutVideoProps> = ({src, fps, segments}) => {
  let from = 0;
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {segments.map((seg, i) => {
        const duration = Math.max(1, Math.round((seg.end - seg.start) * fps));
        const element = (
          <Sequence key={i} from={from} durationInFrames={duration}>
            <OffthreadVideo
              src={staticFile(src)}
              startFrom={Math.round(seg.start * fps)}
              endAt={Math.round(seg.end * fps)}
            />
          </Sequence>
        );
        from += duration;
        return element;
      })}
    </AbsoluteFill>
  );
};
