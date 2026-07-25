using System.Collections;
using UnityEngine;

public sealed class CollectionManager : MonoBehaviour
{
    private CollectionRepository repository;
    private CollectionView view;
    private ThoughtMapPersonalLibraryApiClient personalApi;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void Bootstrap()
    {
        if (Object.FindFirstObjectByType<CollectionManager>() != null ||
            Object.FindFirstObjectByType<ThoughtMapRuntimeController>() == null)
        {
            return;
        }
        Canvas canvas = Object.FindFirstObjectByType<Canvas>();
        if (canvas == null) return;
        GameObject target = new GameObject("CollectionSystem", typeof(RectTransform), typeof(CollectionManager), typeof(CollectionView));
        target.transform.SetParent(canvas.transform, false);
    }

    private IEnumerator Start()
    {
        repository = new CollectionRepository();
        view = GetComponent<CollectionView>();
        if (GetComponent<ThoughtMapPersonalRepository>() == null) gameObject.AddComponent<ThoughtMapPersonalRepository>();
        view.Build(repository);
        personalApi = GetComponent<ThoughtMapPersonalLibraryApiClient>() ?? gameObject.AddComponent<ThoughtMapPersonalLibraryApiClient>();
        if (!string.IsNullOrWhiteSpace(ThoughtMapPersonalSession.Email))
        {
            StartCoroutine(personalApi.GetSavedByEmail(
                ThoughtMapPersonalSession.Email,
                response => HandleLibraryLoaded(new SavedDocumentsResponse { items = response == null ? null : response.WorksOrItems }),
                HandleLibraryError));
            yield break;
        }
        ThoughtMapApiClient api = Object.FindFirstObjectByType<ThoughtMapApiClient>();
        if (api != null)
        {
            StartCoroutine(api.GetDefaultSaved(HandleLibraryLoaded, HandleLibraryError));
        }
        yield break;
    }

    private void HandleLibraryLoaded(SavedDocumentsResponse response)
    {
        repository.MergePersonalLibrary(response == null ? null : response.items);
        view.Refresh();
    }

    private void HandleLibraryError(string message)
    {
        Debug.LogWarning("[Collection] SQLite/Personal Library refresh unavailable: " + message, this);
        view.Refresh();
    }
}
