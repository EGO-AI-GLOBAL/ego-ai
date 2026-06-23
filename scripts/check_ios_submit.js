/* One-off: check iOS TestFlight submit status via Expo GraphQL */
const fs = require('fs');
const os = require('os');
const path = require('path');
const easRoot = path.join(process.env.APPDATA, 'npm', 'node_modules', 'eas-cli');
const { BuildQuery } = require(path.join(easRoot, 'build/graphql/queries/BuildQuery'));
const { SubmissionQuery } = require(path.join(easRoot, 'build/graphql/queries/SubmissionQuery'));
const { createGraphqlClient } = require(path.join(easRoot, 'build/commandUtils/context/contextUtils/createGraphqlClient'));

function getAuthInfo() {
  const statePath = path.join(os.homedir(), '.expo', 'state.json');
  const auth = JSON.parse(fs.readFileSync(statePath, 'utf8')).auth;
  if (!auth?.sessionSecret && !process.env.EXPO_TOKEN) {
    return null;
  }
  return {
    accessToken: process.env.EXPO_TOKEN || null,
    sessionSecret: auth?.sessionSecret || null,
  };
}

(async () => {
  const authInfo = getAuthInfo();
  if (!authInfo) {
    console.log('NO_SESSION');
    process.exit(2);
  }
  const client = createGraphqlClient(authInfo);
  const buildId = '1f67eb44-7768-410c-99a9-a0ff629bfabc';
  const appId = '558cc924-3323-4d68-a82b-aa237bf16369';

  const build = await BuildQuery.withSubmissionsByIdAsync(client, buildId, { useCache: false });
  console.log('BUILD:', build.appVersion, 'build', build.appBuildVersion, 'status', build.status);
  const onBuild = build.submissions || [];
  console.log('SUBMISSIONS_ON_BUILD:', onBuild.length);
  onBuild.forEach((s) => {
    console.log(
      JSON.stringify({
        id: s.id,
        status: s.status,
        createdAt: s.createdAt,
        completedAt: s.completedAt,
        error: s.error?.message || s.error,
      })
    );
  });

  for (const id of ['de232d57-e26c-478f-977e-18f628ba992d', '07f5b423-68c2-453e-ab0c-cf12e0913621']) {
    const detail = await SubmissionQuery.byIdAsync(client, id, { useCache: false });
    if (detail) {
      console.log('DETAIL', JSON.stringify({
        id: detail.id,
        status: detail.status,
        createdAt: detail.createdAt,
        completedAt: detail.completedAt,
        version: detail.build?.appVersion,
        buildNum: detail.build?.appBuildVersion,
        error: detail.error?.message || detail.error,
      }));
    }
  }

  const subs = await SubmissionQuery.allForAppAsync(client, appId, { limit: 5, platform: 'IOS' });
  console.log('RECENT_IOS:');
  subs.forEach((s) => {
    console.log(
      JSON.stringify({
        id: s.id,
        status: s.status,
        createdAt: s.createdAt,
        completedAt: s.completedAt,
        version: s.build?.appVersion,
        buildNum: s.build?.appBuildVersion,
        error: s.error?.message,
      })
    );
  });
})().catch((e) => {
  console.error('ERR:', e.message || e);
  process.exit(1);
});
