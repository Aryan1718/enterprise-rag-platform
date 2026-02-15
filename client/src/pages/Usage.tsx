import Layout from "../components/layout/Layout";
import TokenMeter from "../components/usage/TokenMeter";

export default function Usage() {
  return (
    <Layout>
      <TokenMeter usage={null} />
    </Layout>
  );
}
