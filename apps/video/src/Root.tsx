import { Composition } from "remotion";
import { ATCExplainer } from "./compositions/ATCExplainer";
import { ATCSimulation } from "./compositions/ATCSimulation";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="ATCExplainer"
        component={ATCExplainer}
        durationInFrames={5660} // ~189 seconds — matches TTS audio
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="ATCSimulation"
        component={ATCSimulation}
        durationInFrames={2180} // ~73 seconds — matches TTS audio
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
